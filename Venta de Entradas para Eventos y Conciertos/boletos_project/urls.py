"""
URLs raíz del proyecto boletos_project.

NO se incluye django.contrib.admin (el sistema no expone admin de Django).
La documentación de la API (Swagger / OpenAPI) queda en /docs/ y /api/schema/,
y todo el sistema se accede por las vistas HTML de la app `boletos`.
"""

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Documentación de la API (enlazada desde el pie de página de cada pantalla)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Vistas HTML + endpoints internos del sistema
    path('', include('boletos.urls')),
]
