"""Configuración de la aplicación `boletos` (venta de entradas)."""

from django.apps import AppConfig


class BoletosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boletos'
    verbose_name = 'Venta de Entradas para Eventos'
    description = (
        'Plataforma de boletería: eventos, sectores, carro persistente, '
        'compras y entradas con código Hash/UUID.'
    )

    def ready(self):
        """Conecta las señales del proyecto (transiciones de estado de Compra)."""
        from . import signals  # noqa: F401
