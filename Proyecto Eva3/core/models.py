"""
Modelos del dominio — Dulce Arte.
Pastelería Artesanal: pedidos, inventario (BOM), kanban y despachos.
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
from django.urls import reverse
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Base abstracta con marcas de creación y actualización."""

    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-creado"]


# ---------------------------------------------------------------------------
# 1. Catálogo
# ---------------------------------------------------------------------------
class Categoria(TimeStampedModel):
    """Categorías de productos: Tortas, Galletas, Cupcakes, etc."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre

    def get_absolute_url(self):
        return reverse("core:categoria_detalle", args=[self.pk])


class Producto(TimeStampedModel):
    """Producto del catálogo pastelero."""

    class Unidad(models.TextChoices):
        UNIDAD = "und", "Unidad"
        GRAMO = "g", "Gramo"
        KILO = "kg", "Kilo"
        PORCION = "por", "Porción"

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="categoría",
    )
    nombre = models.CharField("nombre", max_length=180)
    descripcion = models.TextField("descripción", blank=True)
    precio_base = models.DecimalField(
        "precio base",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    unidad = models.CharField(
        "unidad",
        max_length=10,
        choices=Unidad.choices,
        default=Unidad.UNIDAD,
    )
    imagen = models.CharField(
        "emoji / imagen",
        max_length=10,
        blank=True,
        help_text="Emoji representativo para el catálogo.",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["categoria__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nombre"],
                name="unico_producto_por_categoria",
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.categoria.nombre})"

    def get_absolute_url(self):
        return reverse("core:producto_detalle", args=[self.pk])

    # --- BOM: Lista de Materiales -----------------------------------------
    @property
    def costo_insumos(self) -> Decimal:
        """Costo total de insumos según la Lista de Materiales (BOM)."""
        total = self.componentes.aggregate(
            total=Sum(F("cantidad") * F("insumo__precio_unitario"))
        )["total"]
        return total or Decimal("0")

    @property
    def margen(self) -> Decimal:
        return self.precio_base - self.costo_insumos


class ComponenteProducto(TimeStampedModel):
    """
    Lista de Materiales (BOM): vincula un Producto con sus Insumos
    y la cantidad requerida para producirlo.
    """

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="componentes",
        verbose_name="producto",
    )
    insumo = models.ForeignKey(
        "Insumo",
        on_delete=models.PROTECT,
        related_name="componentes",
        verbose_name="insumo",
    )
    cantidad = models.DecimalField(
        "cantidad",
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Cantidad del insumo necesaria para 1 unidad de producto.",
    )

    class Meta:
        verbose_name = "componente (BOM)"
        verbose_name_plural = "lista de materiales (BOM)"
        ordering = ["producto__nombre", "insumo__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "insumo"],
                name="unico_componente_producto_insumo",
            )
        ]

    def __str__(self) -> str:
        return f"{self.cantidad} × {self.insumo.nombre} → {self.producto.nombre}"

    @property
    def costo_linea(self) -> Decimal:
        return self.cantidad * self.insumo.precio_unitario


# ---------------------------------------------------------------------------
# 2. Inventario
# ---------------------------------------------------------------------------
class Insumo(TimeStampedModel):
    """Insumo de bodega: ingredientes y materiales de pastelería."""

    class Unidad(models.TextChoices):
        GRAMO = "g", "Gramo"
        KILO = "kg", "Kilo"
        MILILITRO = "ml", "Mililitro"
        LITRO = "l", "Litro"
        UNIDAD = "und", "Unidad"
        CAJA = "caja", "Caja"

    nombre = models.CharField("nombre", max_length=180, unique=True)
    unidad = models.CharField("unidad", max_length=10, choices=Unidad.choices, default=Unidad.KILO)
    stock_actual = models.DecimalField(
        "stock actual",
        max_digits=10,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    stock_minimo = models.DecimalField(
        "stock mínimo",
        max_digits=10,
        decimal_places=3,
        default=Decimal("0"),
        help_text="Bajo este nivel se marca como stock bajo.",
    )
    precio_unitario = models.DecimalField(
        "precio unitario",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    proveedor = models.CharField("proveedor", max_length=180, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "insumo"
        verbose_name_plural = "insumos"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.stock_actual} {self.get_unidad_display()})"

    def get_absolute_url(self):
        return reverse("core:insumo_detalle", args=[self.pk])

    @property
    def stock_bajo(self) -> bool:
        return self.stock_actual <= self.stock_minimo

    @property
    def valor_total(self) -> Decimal:
        return self.stock_actual * self.precio_unitario

    def descontar(self, cantidad: Decimal, motivo: str, pedido=None) -> "MovimientoInsumo":
        """Descuenta stock y registra el movimiento (kardex)."""
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0.")
        if self.stock_actual < cantidad:
            raise ValidationError(
                f"Stock insuficiente de {self.nombre}: "
                f"disponible {self.stock_actual}, requerido {cantidad}."
            )
        self.stock_actual = F("stock_actual") - cantidad
        self.save(update_fields=["stock_actual", "actualizado"])
        self.refresh_from_db(fields=["stock_actual"])
        return MovimientoInsumo.objects.create(
            insumo=self,
            tipo=MovimientoInsumo.Tipo.SALIDA,
            cantidad=cantidad,
            motivo=motivo,
            pedido=pedido,
        )

    def reponer(self, cantidad: Decimal, motivo: str = "Reposición manual") -> "MovimientoInsumo":
        """Aumenta stock y registra el movimiento."""
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0.")
        self.stock_actual = F("stock_actual") + cantidad
        self.save(update_fields=["stock_actual", "actualizado"])
        self.refresh_from_db(fields=["stock_actual"])
        return MovimientoInsumo.objects.create(
            insumo=self,
            tipo=MovimientoInsumo.Tipo.ENTRADA,
            cantidad=cantidad,
            motivo=motivo,
        )


class MovimientoInsumo(TimeStampedModel):
    """Kardex de movimientos de inventario (entradas y salidas)."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.CASCADE,
        related_name="movimientos",
        verbose_name="insumo",
    )
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    cantidad = models.DecimalField(
        "cantidad",
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    motivo = models.CharField("motivo", max_length=255)
    pedido = models.ForeignKey(
        "Pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
        verbose_name="pedido",
    )
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_insumo",
        verbose_name="registrado por",
    )

    class Meta:
        verbose_name = "movimiento de insumo"
        verbose_name_plural = "movimientos de insumos"
        ordering = ["-creado"]

    def __str__(self) -> str:
        signo = "+" if self.tipo == self.Tipo.ENTRADA else "−"
        return f"{signo}{self.cantidad} {self.insumo.nombre} · {self.motivo}"


# ---------------------------------------------------------------------------
# 3. Clientes y Pedidos
# ---------------------------------------------------------------------------
class Cliente(TimeStampedModel):
    """Cliente de la pastelería."""

    nombre = models.CharField("nombre", max_length=180)
    email = models.EmailField("correo", blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    comuna = models.CharField("comuna", max_length=120, blank=True)
    notas = models.TextField("notas", blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre

    def get_absolute_url(self):
        return reverse("core:cliente_detalle", args=[self.pk])


class Pedido(TimeStampedModel):
    """
    Pedido personalizado con flujo Kanban:
    Recibido → En Preparación → Horneado/Decorado → Control de Calidad → Listo
    """

    class Estado(models.TextChoices):
        RECIBIDO = "recibido", "Recibido"
        EN_PREPARACION = "preparacion", "En Preparación"
        HORNEADO = "horneado", "Horneado / Decorado"
        CONTROL = "control", "Control de Calidad"
        LISTO = "listo", "Listo"

    class Prioridad(models.TextChoices):
        NORMAL = "normal", "Normal"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    class EstadoDespacho(models.TextChoices):
        PENDIENTE = "pendiente", "Sin despacho"
        EN_RUTA = "en_ruta", "En Ruta"
        ENTREGADO = "entregado", "Entregado"

    numero = models.CharField("número", max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="pedidos",
        verbose_name="cliente",
    )
    # Requerimiento: cotización y registro de pedidos personalizados
    descripcion_diseño = models.TextField(
        "diseño personalizado",
        help_text="Descripción del diseño: colores, decoración, texto en torta, referencias.",
    )
    ingredientes_especiales = models.TextField(
        "ingredientes especiales",
        blank=True,
        help_text="Alergias, ingredientes adicionales o sustituciones.",
    )
    fecha_entrega = models.DateTimeField("fecha y hora de entrega")
    prioridad = models.CharField(
        "prioridad",
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.NORMAL,
    )
    # Requerimiento: Kanban
    estado = models.CharField(
        "estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.RECIBIDO,
        db_index=True,
    )
    # Costos
    subtotal = models.DecimalField(
        "subtotal",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
    )
    descuento = models.DecimalField(
        "descuento",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    total = models.DecimalField(
        "total",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
    )
    # Despacho
    direccion_despacho = models.CharField("dirección de despacho", max_length=255, blank=True)
    estado_despacho = models.CharField(
        "estado de despacho",
        max_length=15,
        choices=EstadoDespacho.choices,
        default=EstadoDespacho.PENDIENTE,
    )
    notas = models.TextField("notas internas", blank=True)
    creador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_creados",
        verbose_name="creado por",
    )
    insumos_descontados = models.BooleanField(
        "insumos descontados",
        default=False,
        help_text="Marca si el BOM ya descontó el inventario.",
    )

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["fecha_entrega"]

    def __str__(self) -> str:
        return f"{self.numero} · {self.cliente.nombre}"

    def get_absolute_url(self):
        return reverse("core:pedido_detalle", args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.numero:
            ultimo = Pedido.objects.order_by("-id").first()
            siguiente = (int(ultimo.numero.split("-")[1]) + 1) if ultimo else 1
            self.numero = f"DA-{siguiente:04d}"
        # Recalcular totales desde los detalles
        if self.pk:
            detalles = self.detalles.all()
            self.subtotal = sum(d.subtotal for d in detalles)
            self.total = max(self.subtotal - self.descuento, Decimal("0"))
        super().save(*args, **kwargs)

    # --- Reglas del Kanban -------------------------------------------------
    ESTADO_ORDEN = [
        Estado.RECIBIDO,
        Estado.EN_PREPARACION,
        Estado.HORNEADO,
        Estado.CONTROL,
        Estado.LISTO,
    ]

    @property
    def estado_indice(self) -> int:
        return self.ESTADO_ORDEN.index(self.estado)

    @property
    def puede_avanzar(self) -> bool:
        return self.estado_indice < len(self.ESTADO_ORDEN) - 1

    @property
    def puede_retroceder(self) -> bool:
        return self.estado_indice > 0

    @property
    def atrasado(self) -> bool:
        return self.fecha_entrega < timezone.now() and self.estado != self.Estado.LISTO

    @property
    def dias_restantes(self) -> int:
        delta = self.fecha_entrega - timezone.now()
        return delta.days

    def avanzar_estado(self) -> "Pedido":
        """Avanza al siguiente estado del tablero Kanban."""
        if not self.puede_avanzar:
            raise ValidationError("El pedido ya está en el último estado.")
        nuevo = self.ESTADO_ORDEN[self.estado_indice + 1]
        # Al pasar a 'listo', garantizar descuento de insumos
        if nuevo == self.Estado.LISTO and not self.insumos_descontados:
            self.descontar_insumos()
        self.estado = nuevo
        self.save(update_fields=["estado", "actualizado"])
        return self

    def retroceder_estado(self) -> "Pedido":
        """Retrocede al estado anterior del tablero Kanban."""
        if not self.puede_retroceder:
            raise ValidationError("El pedido ya está en el primer estado.")
        self.estado = self.ESTADO_ORDEN[self.estado_indice - 1]
        self.save(update_fields=["estado", "actualizado"])
        return self

    def mover_a(self, estado: str) -> "Pedido":
        """Mueve el pedido a un estado específico (validando el flujo)."""
        if estado not in self.ESTADO_ORDEN:
            raise ValidationError("Estado inválido.")
        destino = self.ESTADO_ORDEN.index(estado)
        actual = self.estado_indice
        if abs(destino - actual) > 1:
            raise ValidationError("Solo se puede avanzar o retroceder un paso a la vez.")
        if destino > actual and not self.insumos_descontados and estado == self.Estado.LISTO:
            self.descontar_insumos()
        self.estado = estado
        self.save(update_fields=["estado", "actualizado"])
        return self

    # --- Regla de negocio: descuento por BOM -------------------------------
    def descontar_insumos(self) -> None:
        """
        Descuenta del inventario todos los insumos requeridos por el BOM
        multiplicados por las cantidades de cada detalle del pedido.
        """
        if self.insumos_descontados:
            return
        requerido: dict[int, Decimal] = {}
        for detalle in self.detalles.select_related("producto"):
            for comp in detalle.producto.componentes.select_related("insumo"):
                cantidad = comp.cantidad * detalle.cantidad
                requerido[comp.insumo_id] = requerido.get(comp.insumo_id, Decimal("0")) + cantidad

        for insumo_id, cantidad in requerido.items():
            insumo = Insumo.objects.get(pk=insumo_id)
            insumo.descontar(
                cantidad,
                motivo=f"Producción pedido {self.numero}",
                pedido=self,
            )
        self.insumos_descontados = True
        self.save(update_fields=["insumos_descontados", "actualizado"])

    @property
    def ingredientes_requeridos(self):
        """Agregado de insumos requeridos para producir el pedido."""
        requerido: dict[int, dict] = {}
        for detalle in self.detalles.select_related("producto"):
            for comp in detalle.producto.componentes.select_related("insumo"):
                cantidad = comp.cantidad * detalle.cantidad
                actual = requerido.get(comp.insumo_id)
                if actual:
                    actual["cantidad"] += cantidad
                else:
                    requerido[comp.insumo_id] = {
                        "insumo": comp.insumo,
                        "cantidad": cantidad,
                    }
        return list(requerido.values())


class DetallePedido(TimeStampedModel):
    """Línea de un pedido: producto y cantidad."""

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="pedido",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_pedido",
        verbose_name="producto",
    )
    cantidad = models.PositiveIntegerField("cantidad", default=1)
    precio_unitario = models.DecimalField(
        "precio unitario",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
    )

    class Meta:
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pedido", "producto"],
                name="unico_producto_por_pedido",
            )
        ]

    def __str__(self) -> str:
        return f"{self.cantidad}× {self.producto.nombre}"

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio_base
        super().save(*args, **kwargs)
        # Recalcular totales del pedido
        self.pedido.save()

    @property
    def subtotal(self) -> Decimal:
        return self.cantidad * self.precio_unitario


# ---------------------------------------------------------------------------
# 4. Despachos con firma digital
# ---------------------------------------------------------------------------
class Despacho(TimeStampedModel):
    """Ruta de despacho con confirmación mediante firma digital o comprobante."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_RUTA = "en_ruta", "En Ruta"
        ENTREGADO = "entregado", "Entregado"
        RECHAZADO = "rechazado", "Rechazado"

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="despacho",
        verbose_name="pedido",
    )
    transportista = models.CharField("transportista", max_length=180, blank=True)
    fecha_programada = models.DateTimeField("fecha programada")
    direccion = models.CharField("dirección", max_length=255)
    estado = models.CharField(
        "estado",
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    # Confirmación de entrega
    entregado_en = models.DateTimeField("entregado en", null=True, blank=True)
    recibido_por = models.CharField("recibido por", max_length=180, blank=True)
    firma_digital = models.TextField(
        "firma digital",
        blank=True,
        help_text="Firma capturada en canvas (base64) o comprobante.",
    )
    comprobante = models.FileField(
        "comprobante",
        upload_to="comprobantes/%Y/%m/",
        blank=True,
        null=True,
    )
    observaciones = models.TextField("observaciones", blank=True)

    class Meta:
        verbose_name = "despacho"
        verbose_name_plural = "despachos"
        ordering = ["fecha_programada"]

    def __str__(self) -> str:
        return f"Despacho {self.pedido.numero} → {self.estado}"

    def get_absolute_url(self):
        return reverse("core:despacho_detalle", args=[self.pk])

    @property
    def puede_entregar(self) -> bool:
        return self.estado in (self.Estado.PENDIENTE, self.Estado.EN_RUTA)

    def confirmar_entrega(self, recibido_por: str, firma: str = "", observaciones: str = "") -> "Despacho":
        """Confirma la entrega con firma digital o comprobante."""
        if self.estado == self.Estado.ENTREGADO:
            raise ValidationError("El despacho ya fue entregado.")
        if not firma and not self.comprobante:
            raise ValidationError("Debe adjuntar una firma digital o un comprobante.")
        self.recibido_por = recibido_por
        self.firma_digital = firma
        if observaciones:
            self.observaciones = observaciones
        self.estado = self.Estado.ENTREGADO
        self.entregado_en = timezone.now()
        self.save()
        self.pedido.estado_despacho = Pedido.EstadoDespacho.ENTREGADO
        self.pedido.save(update_fields=["estado_despacho", "actualizado"])
        return self


class Perfil(TimeStampedModel):
    """Extiende User con datos del rol (cocina, despacho, administración)."""

    class Rol(models.TextChoices):
        ADMIN = "admin", "Administración"
        COCINA = "cocina", "Cocina"
        DESPACHO = "despacho", "Despacho"
        VENTA = "venta", "Ventas"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField("rol", max_length=15, choices=Rol.choices, default=Rol.VENTA)
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username} · {self.get_rol_display()}"
