"""
Configuración principal de URLs del proyecto academic_project.

Incluye:
- Admin de Django
- URLs de la app academic (vistas HTML + API DRF)
- Redirección de raíz a courses
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # Panel de administración
    path('admin/', admin.site.urls),

    # App academic - vistas HTML y API
    path('', include('academic.urls')),

    # Redirección de raíz vacía a courses (evita error 404 en "/")
    path('', RedirectView.as_view(url='/courses/', permanent=False)),
]