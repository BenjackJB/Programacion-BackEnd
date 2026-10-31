"""Rutas de vistas de plantillas."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("", views.inicio, name="inicio"),

    path("productos/", views.productos, name="productos"),
    path("productos/<int:pk>/", views.producto_detalle, name="producto_detalle"),

    path("insumos/", views.insumos, name="insumos"),
    path("insumos/<int:pk>/", views.insumo_detalle, name="insumo_detalle"),

    path("pedidos/", views.pedidos, name="pedidos"),
    path("pedidos/<int:pk>/", views.pedido_detalle, name="pedido_detalle"),

    path("kanban/", views.kanban, name="kanban"),
    path("kanban/<int:pk>/mover/", views.kanban_mover, name="kanban_mover"),

    path("clientes/", views.clientes, name="clientes"),
    path("clientes/<int:pk>/", views.cliente_detalle, name="cliente_detalle"),

    path("despachos/", views.despachos, name="despachos"),
    path("despachos/<int:pk>/", views.despacho_detalle, name="despacho_detalle"),

    path("referencia/", views.referencia, name="referencia"),
]
