"""Punto de entrada WSGI del proyecto boletos_project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boletos_project.settings')

application = get_wsgi_application()
