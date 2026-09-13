from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    # Django Admin
    path('django-admin/', admin.site.urls),

    # API app URLs (legacy/admin functionality)
    path('admin/', include('api.urls')),
    path('api/', include('api.api_urls')),

    # Academic app URLs (main app)
    path('', include('academic.urls')),
]