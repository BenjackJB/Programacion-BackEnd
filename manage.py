#!/usr/bin/env python
"""Punto de entrada principal de Django para el proyecto academic_project."""
import os
import sys


def main():
    """Configura el entorno y ejecuta comandos de gestión de Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y en el PYTHONPATH?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()