"""
Vistas del API REST (DRF) del sistema de venta de entradas.

Endpoints principales (la documentación interactiva está en /docs/):
- PÚBLICO      : GET  /api/eventos/  y  GET /api/eventos/{id}/sectores/
- ESPECTADOR   : GET/POST/DELETE /api/carro-tickets/ , POST /api/compras/pagar/
                 y GET /api/mis-entradas/
- ORGANIZADOR  : POST/PUT/DELETE /api/eventos/ y PATCH /api/compras/{id}/estado/

NOTA: el API se sirve SOLO en JSON (sin API browsable) y se consume desde los
templates mediante fetch() con token JWT (Authorization: Bearer <access>).
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Min, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .filters import CompraFilter, EventoFilter
from .models import Carro, CarroItem, Compra, Evento, Recinto, Sector, Ticket
from .permissions import EsDuenioOVorganizador, EsEspectador, EsOrganizador, LecturaPublicaEscrituraOrganizador
from .serializers import (
    AgregarAlCarroSerializer,
    CambioEstadoSerializer,
    CarroSerializer,
    CompraSerializer,
    EventoSerializer,
    RecintoSerializer,
    RegistroSerializer,
    SectorSerializer,
    TicketSerializer,
    TokenConRolSerializer,
    UsuarioSerializer,
)
from .services import procesar_pago


# =============================================================================
# AUTENTICACIÓN: TOKEN JWT CON CLAIM DE ROL, REFRESH Y REGISTRO
# =============================================================================

class TokenConRolView(TokenObtainPairView):
    """POST /api/token/ -> access + refresh con el claim `rol` del usuario."""

    serializer_class = TokenConRolSerializer
    permission_classes = [AllowAny]


class TokenRefreshViewConRol(TokenRefreshView):
    """POST /api/token/refresh/ -> nuevo access token."""

    permission_classes = [AllowAny]


class RegistroView(APIView):
    """
    POST /api/registro/ -> alta de usuario (Espectador u Organizador).
    Devuelve los tokens JWT para iniciar sesión automáticamente.
    """

    permission_classes = [AllowAny]
    serializer_class = RegistroSerializer

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        for token in (refresh, access):
            token['rol'] = user.rol
            token['usuario_id'] = user.pk
            token['es_organizador'] = user.es_organizador
            token['nombre_completo'] = user.nombre_completo

        return Response(
            {
                'access': str(access),
                'refresh': str(refresh),
                'rol': user.rol,
                'usuario': UsuarioSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# CATÁLOGO PÚBLICO: EVENTOS, SECTORES Y RECINTOS
# =============================================================================

class EventoViewSet(viewsets.ModelViewSet):
    """
    GET    /api/eventos/            -> catálogo público (filtros, búsqueda y orden)
    POST   /api/eventos/            -> crear evento (organizador)
    PUT    /api/eventos/{id}/       -> editar evento (dueño)
    DELETE /api/eventos/{id}/       -> borrado lógico (dueño)
    GET    /api/eventos/{id}/sectores/ -> sectores/localidades del evento (público)
    POST   /api/eventos/{id}/sectores/ -> agregar sector (dueño)
    """

    serializer_class = EventoSerializer
    permission_classes = [LecturaPublicaEscrituraOrganizador]
    filterset_class = EventoFilter
    search_fields = ['nombre', 'artista', 'descripcion', 'recinto__nombre']
    ordering_fields = ['fecha', 'nombre', 'artista', 'estado', 'precio_desde']
    ordering = ['fecha']

    def get_queryset(self):
        """Eventos activos; el organizador además ve los suyos desactivados."""
        queryset = Evento.all_objects.select_related('recinto', 'organizador').prefetch_related(
            'sectores'
        ).annotate(precio_desde=Min('sectores__precio'))

        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return queryset
        if user.is_authenticated and getattr(user, 'es_organizador', False):
            return queryset.filter(Q(activo=True) | Q(organizador=user))
        return queryset.filter(activo=True)

    def get_permissions(self):
        """La modificación de un evento exige además ser su dueño (permiso de objeto)."""
        permissions = super().get_permissions()
        es_escritura = self.request and self.request.method not in ('GET', 'HEAD', 'OPTIONS')
        if es_escritura and self.action in ('update', 'partial_update', 'destroy', 'sectores'):
            permissions.append(EsDuenioOVorganizador())
        return permissions

    def perform_create(self, serializer):
        """El evento queda vinculado al organizador autenticado."""
        serializer.save(organizador=self.request.user)

    @action(detail=True, methods=['get', 'post'], url_path='sectores')
    def sectores(self, request, pk=None):
        """GET público con las localidades; POST para agregar una (dueño del evento)."""
        evento = self.get_object()

        if request.method == 'POST':
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data['evento'] = evento.pk
            serializer = SectorSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = SectorSerializer(evento.sectores.filter(activo=True), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='restaurar', permission_classes=[EsOrganizador])
    def restaurar(self, request, pk=None):
        """Restaura un evento desactivado (borrado lógico reversible)."""
        evento = self.get_object()
        if evento.organizador_id != request.user.pk and not request.user.is_superuser:
            return Response({'detail': 'Solo el dueño puede restaurar su evento.'},
                            status=status.HTTP_403_FORBIDDEN)
        evento.restore()
        return Response(EventoSerializer(evento, context={'request': request}).data)


class SectorViewSet(viewsets.ModelViewSet):
    """
    CRUD de sectores/localidades.
    Lectura pública; escritura solo con rol Organizador dueño del evento.
    """

    serializer_class = SectorSerializer
    permission_classes = [LecturaPublicaEscrituraOrganizador, EsDuenioOVorganizador]
    filterset_fields = ['evento', 'nombre']
    ordering_fields = ['precio', 'nombre']
    ordering = ['precio']

    def get_queryset(self):
        queryset = Sector.all_objects.select_related('evento', 'evento__organizador')
        if self.request.user.is_authenticated and (
            self.request.user.is_superuser or getattr(self.request.user, 'es_organizador', False)
        ):
            return queryset
        return queryset.filter(activo=True, evento__activo=True)

    def perform_create(self, serializer):
        """Valida que el sector pertenezca a un evento existente y activo."""
        evento = serializer.validated_data.get('evento')
        if evento is None:
            raise ValidationError({'evento': 'Debes indicar el evento del sector.'})
        if not evento.activo:
            raise ValidationError({'evento': 'El evento ya no está disponible.'})
        serializer.save()


class RecintoViewSet(viewsets.ModelViewSet):
    """CRUD de recintos/locales. Lectura pública, escritura con rol Organizador."""

    serializer_class = RecintoSerializer
    permission_classes = [LecturaPublicaEscrituraOrganizador]
    search_fields = ['nombre', 'ciudad', 'direccion']
    ordering_fields = ['nombre', 'ciudad']
    ordering = ['nombre']

    def get_queryset(self):
        if self.request.user.is_authenticated and (
            self.request.user.is_superuser or getattr(self.request.user, 'es_organizador', False)
        ):
            return Recinto.all_objects.all()
        return Recinto.objects.all()


# =============================================================================
# CARRO DE COMPRAS PERSISTENTE (ESPECTADOR)
# =============================================================================

class CarroViewSet(viewsets.GenericViewSet):
    """
    GET    /api/carro-tickets/      -> carro activo del usuario (persistente)
    POST   /api/carro-tickets/      -> agregar/sumar ítems {sector, cantidad}
    DELETE /api/carro-tickets/      -> vaciar el carro
    DELETE /api/carro-tickets/{id}/ -> quitar un ítem del carro

    El carro vive en la base de datos vinculado 1 a 1 al usuario: conserva sus
    ítems al cerrar sesión o al entrar desde otro dispositivo. El stock NO se
    descuenta aquí; se valida y descuenta únicamente al pagar.
    """

    queryset = Carro.objects.none()  # se define en get_queryset (evita avisos del generador de esquema)
    serializer_class = CarroSerializer
    permission_classes = [EsEspectador]

    def get_queryset(self):
        return Carro.objects.filter(usuario=self.request.user)

    def _respuesta(self, carro, code=status.HTTP_200_OK):
        return Response(CarroSerializer(carro).data, status=code)

    def list(self, request):
        """GET /api/carro-tickets/ - devuelve (o crea) el carro del usuario."""
        carro = Carro.obtener_o_crear(request.user)
        return self._respuesta(carro)

    def create(self, request):
        """POST /api/carro-tickets/ - agrega entradas de un sector al carro."""
        serializer = AgregarAlCarroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sector = serializer.validated_data['sector']
        cantidad = serializer.validated_data['cantidad']

        carro = Carro.obtener_o_crear(request.user)
        item = CarroItem.all_objects.filter(carro=carro, sector=sector).first()
        if item is not None:
            # Sin duplicados: si ya existe el sector se suma la cantidad.
            item.cantidad += cantidad
            item.precio_unitario = sector.precio
            item.save(update_fields=['cantidad', 'precio_unitario', 'fecha_actualizacion'])
        else:
            CarroItem.objects.create(
                carro=carro,
                sector=sector,
                cantidad=cantidad,
                precio_unitario=sector.precio,
            )
        return self._respuesta(carro, status.HTTP_201_CREATED)

    @extend_schema(operation_id='carro_item_destroy', summary='Quitar un ítem del carro')
    def destroy(self, request, pk=None):
        """DELETE /api/carro-tickets/{id}/ - elimina un ítem (borrado físico)."""
        carro = Carro.obtener_o_crear(request.user)
        eliminados = CarroItem.all_objects.filter(pk=pk, carro=carro).delete()
        if not eliminados[0]:
            raise ValidationError({'item': 'El ítem no existe en tu carro.'})
        return self._respuesta(carro)

    @extend_schema(operation_id='carro_vaciar', summary='Vaciar el carro de compras')
    @action(detail=False, methods=['delete'], url_path='vaciar')
    def vaciar(self, request):
        """DELETE /api/carro-tickets/vaciar/ - vacía el carro por completo."""
        carro = Carro.obtener_o_crear(request.user)
        carro.vaciar()
        return self._respuesta(carro)


# =============================================================================
# COMPRAS / ÓRDENES: PAGO (ESPECTADOR) Y GESTIÓN DE ESTADOS (ORGANIZADOR)
# =============================================================================

class CompraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET   /api/compras/            -> ventas/órdenes (organizador) o las propias
    GET   /api/compras/{id}/       -> detalle de la orden con sus tickets
    POST  /api/compras/pagar/      -> checkout: valida stock, descuenta y emite tickets
    PATCH /api/compras/{id}/estado/-> ENTREGADO / CANCELADO (organizador)
    """

    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = CompraFilter
    search_fields = ['codigo', 'comprador__username', 'observacion']
    ordering_fields = ['fecha_creacion', 'total', 'estado', 'fecha_pago']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        """El organizador ve todas las ventas; el espectador solo las suyas."""
        user = self.request.user
        if not user.is_authenticated:
            return Compra.objects.none()
        queryset = Compra.all_objects.select_related('comprador').prefetch_related(
            'tickets__sector', 'tickets__evento', 'tickets__evento__recinto', 'historial'
        )
        if user.is_superuser or getattr(user, 'es_organizador', False):
            return queryset
        return queryset.filter(comprador=user)

    def get_permissions(self):
        """
        Permisos por acción (la vista se enruta manualmente, por lo que se
        aplican aquí en lugar de los kwargs del decorador @action):
        - pagar   : solo rol Espectador.
        - estado  : solo rol Organizador.
        - resto   : cualquier usuario autenticado (dueño de sus órdenes).
        """
        if self.action == 'pagar':
            return [EsEspectador()]
        if self.action == 'estado':
            return [EsOrganizador()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='pagar')
    def pagar(self, request):
        """POST /api/compras/pagar/ - confirma el pedido y procesa el pago."""
        compra = procesar_pago(request.user, request.data.get('observacion', ''))
        return Response(CompraSerializer(compra).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='estado')
    def estado(self, request, pk=None):
        """
        PATCH /api/compras/{id}/estado/
        Cambia el estado de la orden (ENTREGADO marca asistencia;
        CANCELADO libera/repon el stock y anula los tickets).
        """
        serializer = CambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        compra = self.get_object()
        try:
            compra.cambiar_estado(
                serializer.validated_data['estado'],
                usuario=request.user,
                observacion=serializer.validated_data.get('observacion', ''),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)

        return Response(CompraSerializer(compra).data)


# =============================================================================
# MIS ENTRADAS (ESPECTADOR)
# =============================================================================

class MisEntradasViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /api/mis-entradas/ -> entradas emitidas al usuario autenticado."""

    queryset = Ticket.objects.none()  # se define en get_queryset
    serializer_class = TicketSerializer
    permission_classes = [EsEspectador]
    filterset_fields = ['estado', 'evento', 'sector']
    ordering_fields = ['fecha_creacion', 'estado']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        return Ticket.all_objects.select_related(
            'compra', 'compra__comprador', 'sector', 'evento', 'evento__recinto'
        ).filter(compra__comprador=self.request.user)
