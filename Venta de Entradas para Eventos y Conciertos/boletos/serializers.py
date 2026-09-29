"""
Serializadores del API (DRF).

Incluye:
- TokenConRolSerializer : token JWT access/refresh con claims de rol.
- RegistroSerializer     : alta de usuarios (Espectador u Organizador).
- Serializadores de catálogo: Evento, Sector, Recinto.
- Serializadores transaccionales: Carro, CarroItem, Compra, Ticket.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Carro,
    CarroItem,
    Compra,
    CompraHistorial,
    Evento,
    Recinto,
    Sector,
    Ticket,
    User,
)


# =============================================================================
# AUTENTICACIÓN (JWT CON CLAIM DE ROL) Y USUARIOS
# =============================================================================

class TokenConRolSerializer(TokenObtainPairSerializer):
    """
    Emite access/refresh e inyecta claims personalizados en el payload:
    rol, usuario_id, es_organizador y nombre_completo (exigido por la rúbrica).
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = user.rol
        token['usuario_id'] = user.pk
        token['es_organizador'] = user.es_organizador
        token['nombre_completo'] = user.nombre_completo
        return token

    def validate(self, attrs):
        """Además de los tokens devuelve el rol y el usuario para el frontend."""
        data = super().validate(attrs)
        data['rol'] = self.user.rol
        data['usuario'] = UsuarioSerializer(self.user).data
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    """Representación pública de un usuario (sin datos sensibles)."""

    nombre_completo = serializers.CharField(read_only=True)
    es_organizador = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'nombre_completo', 'rol', 'es_organizador', 'telefono',
        )
        read_only_fields = ('id', 'username')


class RegistroSerializer(serializers.ModelSerializer):
    """Alta de usuarios con validación de contraseña y selección de rol."""

    password = serializers.CharField(
        write_only=True, min_length=8, style={'input_type': 'password'}
    )
    rol = serializers.ChoiceField(choices=User.Rol.choices, default=User.Rol.ESPECTADOR)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'password', 'rol', 'telefono')

    def validate_password(self, value):
        """Aplica los validadores de contraseña de Django."""
        validate_password(value)
        return value

    def create(self, validated_data):
        """Crea el usuario con contraseña encriptada (no se guarda en texto plano)."""
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# =============================================================================
# CATÁLOGO: REINTO, EVENTO Y SECTOR
# =============================================================================

class SectorSerializer(serializers.ModelSerializer):
    """Sector/localidad de un evento con su precio y stock."""

    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    agotado = serializers.BooleanField(read_only=True)
    vendidas = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sector
        fields = (
            'id', 'evento', 'evento_nombre', 'nombre', 'precio',
            'stock_total', 'stock_disponible', 'vendidas', 'agotado',
            'fecha_creacion', 'fecha_actualizacion',
        )
        read_only_fields = ('fecha_creacion', 'fecha_actualizacion')

    def validate(self, attrs):
        """El stock disponible nunca puede superar al stock total."""
        stock_total = attrs.get('stock_total', getattr(self.instance, 'stock_total', None))
        stock_disponible = attrs.get(
            'stock_disponible',
            stock_total if 'stock_total' in attrs else getattr(self.instance, 'stock_disponible', None),
        )
        if stock_total is not None and stock_disponible is not None:
            if stock_disponible > stock_total:
                raise serializers.ValidationError(
                    {'stock_disponible': 'El stock disponible no puede superar al stock total.'}
                )
        return attrs


class EventoSerializer(serializers.ModelSerializer):
    """Evento con sectores anidados y datos calculados (precio mínimo y stock)."""

    sectores = SectorSerializer(many=True, read_only=True)
    recinto_nombre = serializers.CharField(source='recinto.nombre', read_only=True)
    organizador = serializers.PrimaryKeyRelatedField(read_only=True)
    organizador_nombre = serializers.CharField(source='organizador.username', read_only=True)
    precio_minimo = serializers.DecimalField(max_digits=10, decimal_places=0, read_only=True)
    entradas_disponibles = serializers.IntegerField(read_only=True)
    agotado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Evento
        fields = (
            'id', 'nombre', 'artista', 'descripcion', 'categoria', 'estado',
            'fecha', 'imagen_url', 'recinto', 'recinto_nombre',
            'organizador', 'organizador_nombre',
            'sectores', 'precio_minimo', 'entradas_disponibles', 'agotado',
            'activo', 'fecha_creacion', 'fecha_actualizacion',
        )
        read_only_fields = ('fecha_creacion', 'fecha_actualizacion')


class RecintoSerializer(serializers.ModelSerializer):
    """Recinto/local donde se realiza el evento."""

    class Meta:
        model = Recinto
        fields = (
            'id', 'nombre', 'direccion', 'ciudad', 'capacidad', 'descripcion',
            'fecha_creacion', 'fecha_actualizacion',
        )


# =============================================================================
# CARRO DE COMPRAS PERSISTENTE
# =============================================================================

class CarroItemSerializer(serializers.ModelSerializer):
    """Ítem del carro con sector anidado y subtotals calculados."""

    sector_detalle = SectorSerializer(source='sector', read_only=True)
    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = CarroItem
        fields = (
            'id', 'sector', 'sector_detalle', 'evento_nombre',
            'cantidad', 'precio_unitario', 'subtotal',
        )


class CarroSerializer(serializers.ModelSerializer):
    """Carro activo del usuario: ítems, total y cantidad de entradas."""

    items = CarroItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    cantidad_entradas = serializers.IntegerField(read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = Carro
        fields = ('id', 'usuario', 'usuario_nombre', 'items', 'cantidad_entradas', 'total')


class AgregarAlCarroSerializer(serializers.Serializer):
    """
    Payload de alta de ítems en el carro.

    NOTA: aquí NO se valida ni descuenta stock; la disponibilidad se
    valida recién al pagar (POST /api/compras/pagar/).
    """

    sector = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.filter(activo=True))
    cantidad = serializers.IntegerField(min_value=1, max_value=20, default=1)

    def validate_sector(self, sector):
        """El sector debe pertenecer a un evento activo y en venta."""
        if not sector.evento.activo:
            raise serializers.ValidationError('El evento del sector ya no está disponible.')
        return sector


# =============================================================================
# ÓRDENES, HISTORIAL Y TICKETS
# =============================================================================

class EventoResumenSerializer(serializers.ModelSerializer):
    """Resumen de evento incluido dentro de un ticket."""

    recinto_nombre = serializers.CharField(source='recinto.nombre', read_only=True)

    class Meta:
        model = Evento
        fields = ('id', 'nombre', 'artista', 'fecha', 'categoria', 'estado', 'imagen_url', 'recinto_nombre')


class TicketSerializer(serializers.ModelSerializer):
    """Entrada individual con código Hash/UUID único."""

    evento = EventoResumenSerializer(read_only=True)
    sector_nombre = serializers.CharField(source='sector.nombre', read_only=True)
    sector_precio = serializers.DecimalField(
        source='sector.precio', max_digits=10, decimal_places=0, read_only=True
    )
    orden = serializers.CharField(source='compra.codigo', read_only=True)
    estado_orden = serializers.CharField(source='compra.estado', read_only=True)
    comprador = serializers.CharField(source='compra.comprador.username', read_only=True)

    class Meta:
        model = Ticket
        fields = (
            'id', 'codigo', 'estado', 'evento', 'sector', 'sector_nombre',
            'sector_precio', 'orden', 'estado_orden', 'comprador', 'fecha_creacion',
        )


class CompraHistorialSerializer(serializers.ModelSerializer):
    """Registro de cada cambio de estado de la orden."""

    usuario = serializers.CharField(
        source='usuario.username', default=None, read_only=True
    )
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = CompraHistorial
        fields = ('id', 'estado', 'estado_display', 'usuario', 'detalle', 'fecha')


class CompraSerializer(serializers.ModelSerializer):
    """Orden de compra con sus tickets y su historial de estados."""

    tickets = TicketSerializer(many=True, read_only=True)
    historial = CompraHistorialSerializer(many=True, read_only=True)
    comprador_nombre = serializers.CharField(source='comprador.username', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    cantidad_tickets = serializers.IntegerField(read_only=True)

    class Meta:
        model = Compra
        fields = (
            'id', 'codigo', 'comprador', 'comprador_nombre', 'estado', 'estado_display',
            'total', 'fecha_pago', 'observacion', 'cantidad_tickets',
            'tickets', 'historial', 'fecha_creacion', 'fecha_actualizacion',
        )
        read_only_fields = fields


class CambioEstadoSerializer(serializers.Serializer):
    """Payload de cambio de estado de una orden (solo organizador)."""

    estado = serializers.ChoiceField(choices=Compra.Estado.choices)
    observacion = serializers.CharField(required=False, allow_blank=True, max_length=255)
