"""URLs raíz — Dulce Arte."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("", include("core.urls")),
]

# Página 403 propia (roles/permisos) — se dispara con PermissionDenied
handler403 = "core.views.acceso_restringido"

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personalización del admin con templates propios
admin.site.site_header = "Dulce Arte · Administración"
admin.site.site_title = "Dulce Arte Admin"
admin.site.index_title = "Gestión de la pastelería artesanal"
