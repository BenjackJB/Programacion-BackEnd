"""Rutas de la API REST."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"categorias", views.CategoriaViewSet, basename="categoria")
router.register(r"insumos", views.InsumoViewSet, basename="insumo")
router.register(r"productos", views.ProductoViewSet, basename="producto")
router.register(r"clientes", views.ClienteViewSet, basename="cliente")
router.register(r"pedidos", views.PedidoViewSet, basename="pedido")
router.register(r"detalles", views.DetallePedidoViewSet, basename="detalle")
router.register(r"despachos", views.DespachoViewSet, basename="despacho")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", views.login_view, name="api-login"),
    path("auth/logout/", views.logout_view, name="api-logout"),
    path("auth/whoami/", views.whoami, name="api-whoami"),
    path("reportes/kanban/", views.kanban_board, name="api-kanban"),
    path("reportes/dashboard/", views.dashboard, name="api-dashboard"),
]
