"""
URLs de la app boletos.

Agrupa:
- Rutas de las vistas HTML (templates) del sistema.
- Endpoints internos del API REST (JSON) consumidos por el frontend con JWT.
- Una red de seguridad con re_path(): cualquier dirección falsa o rota que
  escriba el usuario (o que deje un enlace viejo) redirige al catálogo.

NO existen rutas de admin de Django ni un índice navegable del API:
la única interfaz visible son las pantallas HTML y su documentación en /docs/.
"""

from django.urls import path, re_path
from django.views.generic import RedirectView

from . import api_views, views

urlpatterns = [
    # =========================================================================
    # VISTAS HTML (TEMPLATES)
    # =========================================================================
    path('', views.RedireccionInicio.as_view(), name='inicio'),
    path('eventos/', views.EventosView.as_view(), name='eventos'),
    path('eventos/<int:pk>/', views.EventoDetalleView.as_view(), name='evento-detalle'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('registro/', views.RegistroView.as_view(), name='registro'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('carro/', views.CarroView.as_view(), name='carro'),
    path('mis-entradas/', views.MisEntradasView.as_view(), name='mis-entradas'),
    path('organizador/eventos/', views.OrganizadorEventosView.as_view(), name='organizador-eventos'),
    path('organizador/ventas/', views.OrganizadorVentasView.as_view(), name='organizador-ventas'),

    # =========================================================================
    # API - AUTENTICACIÓN (JWT access + refresh y registro)
    # =========================================================================
    path('api/token/', api_views.TokenConRolView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', api_views.TokenRefreshViewConRol.as_view(), name='token_refresh'),
    path('api/registro/', api_views.RegistroView.as_view(), name='api-registro'),

    # =========================================================================
    # API - CATÁLOGO PÚBLICO (eventos, sectores y recintos)
    # =========================================================================
    path(
        'api/eventos/',
        api_views.EventoViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api-eventos',
    ),
    path(
        'api/eventos/<int:pk>/',
        api_views.EventoViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='api-evento-detalle',
    ),
    path(
        'api/eventos/<int:pk>/sectores/',
        api_views.EventoViewSet.as_view({'get': 'sectores', 'post': 'sectores'}),
        name='api-evento-sectores',
    ),
    path(
        'api/eventos/<int:pk>/restaurar/',
        api_views.EventoViewSet.as_view({'post': 'restaurar'}),
        name='api-evento-restaurar',
    ),
    path(
        'api/sectores/',
        api_views.SectorViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api-sectores',
    ),
    path(
        'api/sectores/<int:pk>/',
        api_views.SectorViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='api-sector-detalle',
    ),
    path(
        'api/recintos/',
        api_views.RecintoViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api-recintos',
    ),
    path(
        'api/recintos/<int:pk>/',
        api_views.RecintoViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='api-recinto-detalle',
    ),

    # =========================================================================
    # API - CARRO DE COMPRAS PERSISTENTE (espectador)
    # =========================================================================
    path(
        'api/carro-tickets/',
        api_views.CarroViewSet.as_view({'get': 'list', 'post': 'create', 'delete': 'vaciar'}),
        name='api-carro',
    ),
    path(
        'api/carro-tickets/<int:pk>/',
        api_views.CarroViewSet.as_view({'delete': 'destroy'}),
        name='api-carro-item',
    ),

    # =========================================================================
    # API - COMPRAS: PAGO (espectador) Y ESTADOS (organizador)
    # =========================================================================
    path('api/compras/', api_views.CompraViewSet.as_view({'get': 'list'}), name='api-compras'),
    path(
        'api/compras/pagar/',
        api_views.CompraViewSet.as_view({'post': 'pagar'}),
        name='api-pagar',
    ),
    path(
        'api/compras/<int:pk>/',
        api_views.CompraViewSet.as_view({'get': 'retrieve'}),
        name='api-compra-detalle',
    ),
    path(
        'api/compras/<int:pk>/estado/',
        api_views.CompraViewSet.as_view({'patch': 'estado'}),
        name='api-compra-estado',
    ),

    # =========================================================================
    # API - MIS ENTRADAS (espectador)
    # =========================================================================
    path(
        'api/mis-entradas/',
        api_views.MisEntradasViewSet.as_view({'get': 'list'}),
        name='api-mis-entradas',
    ),
    path(
        'api/mis-entradas/<int:pk>/',
        api_views.MisEntradasViewSet.as_view({'get': 'retrieve'}),
        name='api-mis-entrada-detalle',
    ),

    # =========================================================================
    # REDE DE SEGURIDAD (re_path): ENLACES FALSOS O ROTOS -> HOME
    # =========================================================================
    # Se coloca SIEMPRE al final: Django recorre las rutas de arriba hacia
    # abajo, así que solo alcanza a esta expresión regular lo que ninguna otra
    # ruta reclamó. Cualquier dirección inexistente (/cualquier-cosa/) redirige
    # con 302 al catálogo de eventos y conserva la consulta (?search=...).
    #
    # Excepciones deliberadas (deben seguir respondiendo 404, no redirigir):
    # - /api/...  : un endpoint del API no puede "rebotar" a una página HTML.
    # - /admin/...: el admin de Django no existe en este proyecto.
    re_path(
        r'^(?!api/|admin/).*$',
        RedirectView.as_view(pattern_name='eventos', permanent=False, query_string=True),
        name='enlace-roto',
    ),
]
