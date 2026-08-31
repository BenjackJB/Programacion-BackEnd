"""
Configuración de la aplicación academic.
"""
from django.apps import AppConfig


class AcademicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academic'
    verbose_name = 'Gestión Académica'