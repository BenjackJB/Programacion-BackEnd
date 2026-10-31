"""Serializers de Django REST Framework para Dulce Arte."""
from django.contrib.auth.models import User
from rest_framework import serializers

from core.models import (
    Categoria,
    Cliente,
    ComponenteProducto,
    Despacho,
    DetallePedido,
    Insumo,
    MovimientoInsumo,
    Pedido,
    Producto,
)


class CategoriaSerializer(serializers.ModelSerializer):
    total_productos = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "activa", "total_productos", "creado", "actualizado"]
        read_only_fields = ["creado", "actualizado"]


class InsumoSerializer(serializers.ModelSerializer):
    stock_bajo = serializers.BooleanField(read_only=True)
    valor_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    get_unidad_display = serializers.CharField(read_only=True)

    class Meta:
        model = Insumo
        fields = [
            "id", "nombre", "unidad", "get_unidad_display", "stock_actual", "stock_minimo",
            "stock_bajo", "precio_unitario", "valor_total", "proveedor", "activo",
            "creado", "actualizado",
        ]
        read_only_fields = ["creado", "actualizado"]


class ComponenteProductoSerializer(serializers.ModelSerializer):
    insumo_detalle = InsumoSerializer(source="insumo", read_only=True)
    costo_linea = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ComponenteProducto
        fields = ["id", "producto", "insumo", "insumo_detalle", "cantidad", "costo_linea"]
        read_only_fields = ["costo_linea"]


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    costo_insumos = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    componentes = ComponenteProductoSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id", "categoria", "categoria_nombre", "nombre", "descripcion",
            "precio_base", "unidad", "imagen", "activo",
            "costo_insumos", "margen", "componentes", "creado", "actualizado",
        ]
        read_only_fields = ["creado", "actualizado"]


class ClienteSerializer(serializers.ModelSerializer):
    total_pedidos = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            "id", "nombre", "email", "telefono", "direccion", "comuna",
            "notas", "activo", "total_pedidos", "creado", "actualizado",
        ]
        read_only_fields = ["creado", "actualizado"]

    def get_total_pedidos(self, obj) -> int:
        return obj.pedidos.count()


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePedido
        fields = ["id", "pedido", "producto", "producto_nombre", "cantidad", "precio_unitario", "subtotal"]
        read_only_fields = ["precio_unitario", "subtotal"]

    def validate_cantidad(self, value):
        if value < 1:
            raise serializers.ValidationError("La cantidad debe ser al menos 1.")
        return value


class MovimientoInsumoSerializer(serializers.ModelSerializer):
    insumo_nombre = serializers.CharField(source="insumo.nombre", read_only=True)
    get_tipo_display = serializers.CharField(read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoInsumo
        fields = [
            "id", "insumo", "insumo_nombre", "tipo", "get_tipo_display",
            "cantidad", "motivo", "pedido", "registrado_por", "registrado_por_nombre", "creado",
        ]
        read_only_fields = fields

    def get_registrado_por_nombre(self, obj) -> str | None:
        if obj.registrado_por is None:
            return None
        return obj.registrado_por.get_full_name() or obj.registrado_por.username


class PedidoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    get_estado_display = serializers.CharField(read_only=True)
    get_prioridad_display = serializers.CharField(read_only=True)
    atrasado = serializers.BooleanField(read_only=True)
    puede_avanzar = serializers.BooleanField(read_only=True)
    puede_retroceder = serializers.BooleanField(read_only=True)
    estado_indice = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id", "numero", "cliente", "cliente_nombre",
            "descripcion_diseño", "ingredientes_especiales",
            "fecha_entrega", "prioridad", "get_prioridad_display",
            "estado", "get_estado_display", "estado_indice",
            "puede_avanzar", "puede_retroceder", "atrasado",
            "subtotal", "descuento", "total",
            "direccion_despacho", "estado_despacho",
            "notas", "insumos_descontados", "detalles",
            "creado", "actualizado",
        ]
        read_only_fields = ["numero", "subtotal", "total", "insumos_descontados", "creado", "actualizado"]


class DespachoSerializer(serializers.ModelSerializer):
    pedido_numero = serializers.CharField(source="pedido.numero", read_only=True)
    get_estado_display = serializers.CharField(read_only=True)
    puede_entregar = serializers.BooleanField(read_only=True)

    class Meta:
        model = Despacho
        fields = [
            "id", "pedido", "pedido_numero", "transportista", "fecha_programada",
            "direccion", "estado", "get_estado_display", "puede_entregar",
            "entregado_en", "recibido_por", "firma_digital", "comprobante",
            "observaciones", "creado", "actualizado",
        ]
        read_only_fields = ["entregado_en", "creado", "actualizado"]


class UserSerializer(serializers.ModelSerializer):
    rol = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff", "rol"]

    def get_rol(self, obj) -> str:
        perfil = getattr(obj, "perfil", None)
        return perfil.get_rol_display() if perfil else "—"
