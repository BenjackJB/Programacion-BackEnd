"""Vistas de API — Django REST Framework."""
from django.contrib.auth import authenticate
from django.db import models
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Categoria,
    Cliente,
    Despacho,
    DetallePedido,
    Insumo,
    MovimientoInsumo,
    Pedido,
    Producto,
)
from core.decorators import ADMIN, COCINA, DESPACHO, user_tiene_rol


def _prohibido_rol(request, *roles) -> Response | None:
    """Devuelve una respuesta 403 si el usuario no tiene el rol requerido."""
    if not user_tiene_rol(request.user, *roles):
        return Response(
            {"detail": "Su rol no tiene permiso para esta operación."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None

from .serializers import (
    CategoriaSerializer,
    ClienteSerializer,
    DespachoSerializer,
    DetallePedidoSerializer,
    InsumoSerializer,
    MovimientoInsumoSerializer,
    PedidoSerializer,
    ProductoSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Categoria.objects.all()
        activa = self.request.query_params.get("activa")
        if activa is not None:
            qs = qs.filter(activa=activa.lower() in {"1", "true", "si", "sí"})
        return qs.annotate(total_productos=Count("productos", distinct=True))


class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.all()
    serializer_class = InsumoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Insumo.objects.all()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(proveedor__icontains=search))
        solo_bajo = self.request.query_params.get("stock_bajo")
        if solo_bajo in {"1", "true"}:
            qs = qs.filter(stock_actual__lte=models.F("stock_minimo"))
        return qs

    @action(detail=True, methods=["post"], url_path="reponer")
    def reponer(self, request, pk=None):
        """Reponer stock de un insumo."""
        insumo = self.get_object()
        cantidad = request.data.get("cantidad")
        if not cantidad:
            return Response(
                {"detail": "Debe indicar la cantidad a reponer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            movimiento = insumo.reponer(
                float(cantidad),
                motivo=request.data.get("motivo", "Reposición desde API"),
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "detail": f"Stock de {insumo.nombre} repuesto.",
                "stock_actual": str(insumo.stock_actual),
                "movimiento": MovimientoInsumoSerializer(movimiento).data,
            }
        )


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.select_related("categoria").prefetch_related("componentes__insumo")
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.query_params.get("categoria")
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
        if self.request.query_params.get("activo") in {"0", "false"}:
            qs = qs.filter(activo=False)
        return qs


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Cliente.objects.all()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search)
                | Q(email__icontains=search)
                | Q(telefono__icontains=search)
            )
        return qs


class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.select_related("producto", "pedido")
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()


class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.select_related("cliente").prefetch_related("detalles__producto")
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Pedido.objects.select_related("cliente").prefetch_related("detalles__producto")
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        prioridad = self.request.query_params.get("prioridad")
        if prioridad:
            qs = qs.filter(prioridad=prioridad)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(numero__icontains=search)
                | Q(cliente__nombre__icontains=search)
                | Q(descripcion_diseño__icontains=search)
            )
        return qs

    @action(detail=True, methods=["post"], url_path="avanzar")
    def avanzar(self, request, pk=None):
        """Avanza el pedido al siguiente estado del Kanban."""
        denegado = _prohibido_rol(request, COCINA, ADMIN)
        if denegado:
            return denegado
        pedido = self.get_object()
        try:
            pedido.avanzar_estado()
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"], url_path="retroceder")
    def retroceder(self, request, pk=None):
        """Retrocede el pedido al estado anterior."""
        denegado = _prohibido_rol(request, COCINA, ADMIN)
        if denegado:
            return denegado
        pedido = self.get_object()
        try:
            pedido.retroceder_estado()
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"], url_path="mover")
    def mover(self, request, pk=None):
        """Mueve el pedido a un estado específico (de a un paso)."""
        denegado = _prohibido_rol(request, COCINA, ADMIN)
        if denegado:
            return denegado
        pedido = self.get_object()
        estado = request.data.get("estado")
        if not estado:
            return Response(
                {"detail": "Debe indicar el estado destino."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pedido.mover_a(estado)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"], url_path="descontar-insumos")
    def descontar_insumos(self, request, pk=None):
        """Descuenta el inventario según el BOM del pedido."""
        denegado = _prohibido_rol(request, COCINA, ADMIN)
        if denegado:
            return denegado
        pedido = self.get_object()
        try:
            pedido.descontar_insumos()
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "detail": f"Insumos descontados para {pedido.numero}.",
                "ingredientes": [
                    {
                        "insumo": str(i["insumo"]),
                        "cantidad": str(i["cantidad"]),
                    }
                    for i in pedido.ingredientes_requeridos
                ],
            }
        )

    @action(detail=True, methods=["get"], url_path="ingredientes")
    def ingredientes(self, request, pk=None):
        """Lista de insumos requeridos por el pedido (BOM)."""
        pedido = self.get_object()
        return Response(
            [
                {
                    "insumo": str(i["insumo"]),
                    "cantidad": str(i["cantidad"]),
                    "unidad": i["insumo"].get_unidad_display(),
                }
                for i in pedido.ingredientes_requeridos
            ]
        )


class DespachoViewSet(viewsets.ModelViewSet):
    queryset = Despacho.objects.select_related("pedido__cliente")
    serializer_class = DespachoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Despacho.objects.select_related("pedido__cliente")
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    @action(detail=True, methods=["post"], url_path="confirmar-entrega")
    def confirmar_entrega(self, request, pk=None):
        """Confirma la entrega con firma digital (base64) o comprobante."""
        denegado = _prohibido_rol(request, DESPACHO, ADMIN)
        if denegado:
            return denegado
        despacho = self.get_object()
        recibido_por = request.data.get("recibido_por", "").strip()
        firma = request.data.get("firma_digital", "")
        observaciones = request.data.get("observaciones", "")

        if not recibido_por:
            return Response(
                {"detail": "Debe indicar quién recibe el pedido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            despacho.confirmar_entrega(
                recibido_por=recibido_por,
                firma=firma,
                observaciones=observaciones,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DespachoSerializer(despacho).data)


# ---------------------------------------------------------------------------
# Endpoints de reportes / tablero
# ---------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def kanban_board(request):
    """Devuelve los pedidos agrupados por columna del tablero Kanban."""
    denegado = _prohibido_rol(request, COCINA, ADMIN)
    if denegado:
        return denegado
    board = {}
    for clave, etiqueta in Pedido.Estado.choices:
        pedidos = Pedido.objects.filter(estado=clave).select_related("cliente")
        board[clave] = {
            "etiqueta": etiqueta,
            "total": pedidos.count(),
            "pedidos": PedidoSerializer(pedidos, many=True).data,
        }
    return Response(board)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """KPIs del panel de control."""
    pedidos = Pedido.objects.all()
    insumos = Insumo.objects.all()

    data = {
        "pedidos_total": pedidos.count(),
        "pedidos_recibidos": pedidos.filter(estado=Pedido.Estado.RECIBIDO).count(),
        "pedidos_en_preparacion": pedidos.filter(estado=Pedido.Estado.EN_PREPARACION).count(),
        "pedidos_listos": pedidos.filter(estado=Pedido.Estado.LISTO).count(),
        "pedidos_atrasados": sum(1 for p in pedidos if p.atrasado),
        "ingresos_totales": str(pedidos.aggregate(t=Sum("total"))["t"] or 0),
        "insumos_total": insumos.count(),
        "insumos_stock_bajo": sum(1 for i in insumos if i.stock_bajo),
        "despachos_pendientes": Despacho.objects.filter(
            estado__in=[Despacho.Estado.PENDIENTE, Despacho.Estado.EN_RUTA]
        ).count(),
        "despachos_entregados": Despacho.objects.filter(estado=Despacho.Estado.ENTREGADO).count(),
        "clientes_total": Cliente.objects.filter(activo=True).count(),
        "movimientos_recientes": MovimientoInsumoSerializer(
            MovimientoInsumo.objects.select_related("insumo", "registrado_por")[:10], many=True
        ).data,
    }
    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Login con sesiones (usado por el frontend JS)."""
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {
            "detail": "Sesión iniciada.",
            "user": {
                "id": user.id,
                "username": user.username,
                "nombre": user.get_full_name() or user.username,
                "is_staff": user.is_staff,
            },
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return Response({"detail": "Sesión cerrada."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def whoami(request):
    perfil = getattr(request.user, "perfil", None)
    return Response(
        {
            "id": request.user.id,
            "username": request.user.username,
            "nombre": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
            "is_staff": request.user.is_staff,
            "rol": perfil.get_rol_display() if perfil else "—",
        }
    )
