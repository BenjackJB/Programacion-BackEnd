from django.contrib import admin
from django.urls import path, include  # <-- Asegúrate de que tenga ", include"
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # <-- Revisa que tenga las comillas y la coma al final
]
