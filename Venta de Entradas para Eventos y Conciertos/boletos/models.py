"""
Modelos de datos del sistema de venta de entradas para eventos y conciertos.

Entidades principales:
- User            : Usuarios del sistema con rol (Espectador / Organizador)
- BaseModel       : Plantilla abstracta con borrado lógico y auditoría
- Recinto         : Locales/estadios donde se realizan los eventos
- Evento          : Conciertos, festivales, etc. (nombre, artista, fecha, recinto)
- Sector          : Localidades del evento (Cancha General, VIP, Tribuna...) con
                    precio propio y stock total de entradas
- Carro           : Carro de compras persistente 1 a 1 con el usuario
- CarroItem       : Ítems del carro (sector + cantidad + precio al momento de agregar)
- Compra          : Orden/transacción con estados PENDIENTE -> PAGADO -> ENTREGADO / CANCELADO
- CompraHistorial : Auditoría de cada cambio de estado de la orden
- Ticket          : Entrada individual con código Hash/UUID único

Reglas de negocio clave implementadas aquí:
- El stock NO se descuenta al agregar al carro: solo cuando la orden pasa a PAGADO.
- Si la orden pasa a CANCELADO se repone automáticamente el stock descontado.
- El carro es un recurso de base de datos vinculado 1 a 1 al usuario: sus ítems
  persisten al cerrar sesión o al entrar desde otro dispositivo.

Los efectos de cada transición (descuento/reposición de stock, emisión y
anulación de tickets, marca de asistencia) viven en las SEÑALES de
boletos/signals.py, conectadas desde boletos/apps.py.
"""

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Manager
from django.utils import timezone


# =============================================================================
# MANAGERS Y MODELO BASE CON BORRADO LÓGICO
# =============================================================================

class ActiveManager(Manager):
    """Manager que filtra solo registros activos (activo=True)."""

    def get_queryset(self):
        return super().get_queryset().filter(activo=True)

    def all_with_inactive(self):
        """Retorna todos los registros incluyendo inactivos."""
        return super().get_queryset()


class BaseModel(models.Model):
    """
    Modelo base abstracto con borrado lógico (soft delete) y auditoría.
    Todos los modelos de catálogo heredan: id, activo, fecha_creacion,
    fecha_actualizacion y los managers objects/all_objects.
    """

    id = models.BigAutoField(primary_key=True, verbose_name='ID')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')

    objects = ActiveManager()
    all_objects = Manager()

    class Meta:
        abstract = True
        ordering = ['-fecha_creacion']

    def soft_delete(self):
        """Borrado lógico: desactiva el registro sin eliminarlo de la base de datos."""
        self.activo = False
        self.save(update_fields=['activo', 'fecha_actualizacion'])

    def restore(self):
        """Restaura un registro desactivado."""
        self.activo = True
        self.save(update_fields=['activo', 'fecha_actualizacion'])

    def delete(self, using=None, keep_parents=False):
        """Fuerza siempre el borrado lógico (nunca DELETE físico)."""
        self.soft_delete()

    def _es_operacion_soft_delete(self, update_fields):
        """Indica si la operación corresponde a un soft delete/restore."""
        if not update_fields:
            return False
        return set(update_fields).issubset({'activo', 'fecha_actualizacion'})


# =============================================================================
# USUARIO CON ROL (Espectador / Organizador)
# =============================================================================

class User(AbstractUser):
    """
    Usuario propio del sistema.

    El campo `rol` alimenta el claim `rol` del token JWT y determina los
    permisos: Espectador (carro, pago y entradas) y Organizador (eventos,
    sectores, ventas y cambio de estado de órdenes).
    """

    class Rol(models.TextChoices):
        ESPECTADOR = 'espectador', 'Espectador'
        ORGANIZADOR = 'organizador', 'Organizador'

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.ESPECTADOR,
        verbose_name='Rol',
        help_text='Rol del usuario para autorización en la API (claim JWT).',
    )
    telefono = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.get_rol_display()})'

    @property
    def es_organizador(self):
        """True si el usuario tiene rol Organizador."""
        return self.rol == self.Rol.ORGANIZADOR

    @property
    def nombre_completo(self):
        """Nombre completo o username como respaldo."""
        return self.get_full_name() or self.username


# =============================================================================
# RECINTO (LOCAL/ESTADIO)
# =============================================================================

class Recinto(BaseModel):
    """Local o estadio donde se realiza un evento (FK de Evento)."""

    nombre = models.CharField(max_length=120, verbose_name='Nombre')
    direccion = models.CharField(max_length=200, blank=True, verbose_name='Dirección')
    ciudad = models.CharField(max_length=100, default='Santiago', verbose_name='Ciudad')
    capacidad = models.PositiveIntegerField(default=0, verbose_name='Capacidad')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')

    class Meta:
        db_table = 'recinto'
        verbose_name = 'Recinto'
        verbose_name_plural = 'Recintos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.ciudad})'


# =============================================================================
# EVENTO
# =============================================================================

class Evento(BaseModel):
    """Evento masivo (concierto, festival, ...) con múltiples sectores/localidades."""

    class Categoria(models.TextChoices):
        CONCIERTO = 'concierto', 'Concierto'
        FESTIVAL = 'festival', 'Festival'
        TEATRO = 'teatro', 'Teatro / Escena'
        DEPORTE = 'deporte', 'Deporte'
        OTRO = 'otro', 'Otro'

    class Estado(models.TextChoices):
        PROXIMO = 'proximo', 'Próximo'
        EN_VENTA = 'en_venta', 'En venta'
        FINALIZADO = 'finalizado', 'Finalizado'
        CANCELADO = 'cancelado', 'Cancelado'

    nombre = models.CharField(max_length=150, verbose_name='Nombre del evento')
    artista = models.CharField(
        max_length=150,
        verbose_name='Artista / Banda',
        help_text='Artista o banda principal del evento.',
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.CONCIERTO,
        verbose_name='Categoría',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.EN_VENTA,
        verbose_name='Estado',
    )
    fecha = models.DateTimeField(verbose_name='Fecha y hora de realización')
    imagen_url = models.URLField(
        blank=True,
        verbose_name='Imagen (URL)',
        help_text='Imagen de portada del evento.',
    )
    recinto = models.ForeignKey(
        Recinto,
        on_delete=models.PROTECT,
        related_name='eventos',
        verbose_name='Recinto / Local',
    )
    organizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='eventos_organizados',
        verbose_name='Organizador',
    )

    class Meta:
        db_table = 'evento'
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['fecha']

    def __str__(self):
        return f'{self.nombre} - {self.artista}'

    @property
    def precio_minimo(self):
        """Precio del sector más barato del evento (0 si no tiene sectores)."""
        precios = self.sectores.filter(activo=True).values_list('precio', flat=True)
        return min(precios) if precios else 0

    @property
    def entradas_disponibles(self):
        """Suma de stock disponible entre todos sus sectores activos."""
        return sum(s.stock_disponible for s in self.sectores.filter(activo=True))

    @property
    def agotado(self):
        """True si el evento no tiene entradas disponibles."""
        return self.entradas_disponibles <= 0


# =============================================================================
# SECTOR (LOCALIDAD)
# =============================================================================

class Sector(BaseModel):
    """
    Localidad/sector del evento (Cancha General, VIP, Tribuna...).
    Cada sector tiene su propio precio y su stock total/disponible.

    IMPORTANTE: el stock solo se descuenta cuando una orden pasa a PAGADO.
    """

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='sectores',
        verbose_name='Evento',
    )
    nombre = models.CharField(max_length=80, verbose_name='Nombre del sector')
    precio = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Precio (CLP)')
    stock_total = models.PositiveIntegerField(verbose_name='Stock total de entradas')
    stock_disponible = models.PositiveIntegerField(
        verbose_name='Stock disponible',
        help_text='Entradas disponibles para la venta (se descuenta solo al pagar).',
    )

    class Meta:
        db_table = 'sector'
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectores'
        ordering = ['precio']
        constraints = [
            models.UniqueConstraint(fields=['evento', 'nombre'], name='sector_unico_por_evento'),
        ]

    def __str__(self):
        return f'{self.nombre} - {self.evento.nombre}'

    def clean(self):
        """Validaciones de integridad del stock."""
        if self.stock_disponible > self.stock_total:
            raise ValidationError({'stock_disponible': 'No puede superar al stock total.'})

    def save(self, *args, **kwargs):
        """Ejecuta validaciones salvo en operaciones de soft delete/restore."""
        if not self._es_operacion_soft_delete(kwargs.get('update_fields')):
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def agotado(self):
        """True cuando no quedan entradas en el sector."""
        return self.stock_disponible <= 0

    @property
    def vendidas(self):
        """Entradas vendidas (stock total - disponible)."""
        return max(self.stock_total - self.stock_disponible, 0)


# =============================================================================
# CARRO DE COMPRAS PERSISTENTE (1 a 1 con el usuario)
# =============================================================================

class Carro(BaseModel):
    """
    Carro de compras persistente en PostgreSQL.

    Relación 1 a 1 con el usuario: los ítems agregados permanecen intactos
    al cerrar sesión o al iniciar sesión desde otro dispositivo.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carro',
        verbose_name='Usuario',
    )

    class Meta:
        db_table = 'carro'
        verbose_name = 'Carro de compras'
        verbose_name_plural = 'Carros de compras'
        ordering = ['-fecha_actualizacion']

    def __str__(self):
        return f'Carro de {self.usuario.username} ({self.items.count()} ítems)'

    @classmethod
    def obtener_o_crear(cls, usuario):
        """Obtiene el carro activo del usuario o lo crea (garantiza relación 1 a 1)."""
        carro, _ = cls.all_objects.get_or_create(usuario=usuario)
        return carro

    @property
    def total(self):
        """Suma de los subtotales de todos los ítems del carro."""
        return sum((item.subtotal for item in self.items.all()), 0)

    @property
    def cantidad_entradas(self):
        """Cantidad total de entradas (todos los ítems)."""
        return sum(item.cantidad for item in self.items.all())

    def vaciar(self):
        """Elimina físicamente todos los ítems del carro (permite re-agregar después)."""
        CarroItem.all_objects.filter(carro=self).delete()


class CarroItem(BaseModel):
    """
    Ítem del carro: un sector con una cantidad de entradas.

    Restricción única (carro, sector): no se permiten duplicados del mismo
    producto; si se vuelve a agregar se incrementa la cantidad existente.
    El precio se congela al momento de agregar el ítem.
    """

    carro = models.ForeignKey(
        Carro,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Carro',
    )
    sector = models.ForeignKey(
        Sector,
        on_delete=models.CASCADE,
        related_name='carro_items',
        verbose_name='Sector',
    )
    cantidad = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name='Precio unitario al agregar',
    )

    class Meta:
        db_table = 'carro_item'
        verbose_name = 'Ítem del carro'
        verbose_name_plural = 'Ítems del carro'
        ordering = ['fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['carro', 'sector'], name='item_unico_por_carro'),
        ]

    def __str__(self):
        return f'{self.cantidad} x {self.sector.nombre}'

    @property
    def subtotal(self):
        """Cantidad x precio unitario."""
        return self.precio_unitario * self.cantidad

    @property
    def evento(self):
        """Evento al que pertenece el sector del ítem."""
        return self.sector.evento


# =============================================================================
# COMPRA (ORDEN / TRANSACCIÓN) Y SU HISTORIAL DE ESTADOS
# =============================================================================

class Compra(BaseModel):
    """
    Orden de compra generada en el checkout (pago).

    Estados (CHOICES explícito):
        PENDIENTE -> PAGADO -> ENTREGADO
                              -> CANCELADO
    Reglas:
    - El stock se descuenta EXCLUSIVAMENTE al pasar a PAGADO.
    - Al pasar a CANCELADO se repone el stock y se anulan los tickets.
    - Al pasar a ENTREGADO se marca la asistencia/ingreso en los tickets.
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de pago'
        PAGADO = 'PAGADO', 'Pagado'
        ENTREGADO = 'ENTREGADO', 'Entregado / Ingresado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    # Transiciones permitidas entre estados (ciclo de vida de la transacción).
    TRANSICIONES = {
        'PENDIENTE': {'PAGADO', 'CANCELADO'},
        'PAGADO': {'ENTREGADO', 'CANCELADO'},
        'ENTREGADO': set(),
        'CANCELADO': set(),
    }

    codigo = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='Código de la orden',
    )
    comprador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='compras',
        verbose_name='Comprador',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name='Estado',
    )
    total = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Total (CLP)')
    fecha_pago = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de pago')
    observacion = models.CharField(max_length=255, blank=True, verbose_name='Observación')

    class Meta:
        db_table = 'compra'
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Orden {str(self.codigo)[:8]} - {self.get_estado_display()}'

    @property
    def cantidad_tickets(self):
        """Cantidad de entradas emitidas en la orden."""
        return self.tickets.count()

    def puede_pasar_a(self, nuevo_estado):
        """Valida si la transición solicitada es legal."""
        return nuevo_estado in self.TRANSICIONES.get(self.estado, set())

    @transaction.atomic
    def cambiar_estado(self, nuevo_estado, usuario=None, observacion=''):
        """
        Cambia el estado de la orden validando el ciclo de vida y auditando
        el cambio en CompraHistorial.

        Los efectos sobre inventario y tickets los ejecuta la señal
        `aplicar_efectos_de_transicion` (ver boletos/signals.py):
        - CANCELADO: repone el stock descontado y anula los tickets.
        - ENTREGADO: marca los tickets como ingresados (asistencia).
        """
        if nuevo_estado not in dict(self.Estado.choices):
            raise ValidationError({'estado': 'Estado desconocido.'})
        if not self.puede_pasar_a(nuevo_estado):
            raise ValidationError({
                'estado': f'No se puede pasar de {self.get_estado_display()} '
                          f'a {dict(self.Estado.choices)[nuevo_estado]}.',
            })

        self.estado = nuevo_estado
        if nuevo_estado == self.Estado.PAGADO and not self.fecha_pago:
            self.fecha_pago = timezone.now()
        if observacion:
            self.observacion = observacion
        # La señal de transiciones aplica aquí los efectos (stock y tickets).
        self.save(update_fields=['estado', 'fecha_pago', 'observacion', 'fecha_actualizacion'])

        # Auditoría del cambio de estado.
        CompraHistorial.objects.create(
            compra=self,
            estado=nuevo_estado,
            usuario=usuario,
            detalle=observacion or f'Estado cambiado a {self.get_estado_display()}',
        )
        return self


class CompraHistorial(models.Model):
    """Auditoría de cada transición de estado de una orden."""

    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Orden',
    )
    estado = models.CharField(max_length=20, choices=Compra.Estado.choices, verbose_name='Estado')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cambios_estado_compras',
        verbose_name='Usuario',
    )
    detalle = models.CharField(max_length=255, verbose_name='Detalle')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        db_table = 'compra_historial'
        verbose_name = 'Historial de orden'
        verbose_name_plural = 'Historial de órdenes'
        ordering = ['fecha']

    def __str__(self):
        return f'{self.compra} -> {self.estado}'


# =============================================================================
# TICKET (ENTRADA EMITIDA)
# =============================================================================

class Ticket(BaseModel):
    """
    Entrada individual emitida al confirmar el pago.

    Cada ticket lleva un código Hash/UUID único que se escanea al ingresar.
    """

    class Estado(models.TextChoices):
        VALIDO = 'VALIDO', 'Válido'
        INGRESADO = 'INGRESADO', 'Ingresado / Asistió'
        CANCELADO = 'CANCELADO', 'Cancelado'

    codigo = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        verbose_name='Código Hash/UUID',
    )
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name='Orden',
    )
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name='Sector',
    )
    evento = models.ForeignKey(
        Evento,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name='Evento',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.VALIDO,
        verbose_name='Estado',
    )

    class Meta:
        db_table = 'ticket'
        verbose_name = 'Entrada'
        verbose_name_plural = 'Entradas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.codigo} - {self.evento.nombre}'

    @staticmethod
    def generar_codigo():
        """Genera un código Hash/UUID único (hex de 32 caracteres)."""
        return uuid.uuid4().hex

    @property
    def comprador(self):
        """Comprador de la orden a la que pertenece el ticket."""
        return self.compra.comprador
