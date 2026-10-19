"""
Configuración principal del proyecto Django boletos_project.

Sistema de venta de entradas para eventos y conciertos (boletería).

Incluye:
- Apps instaladas (Django REST Framework, django-filter, drf-spectacular, boletos)
- Base de datos PostgreSQL (con respaldo SQLite opcional para desarrollo local)
- Autenticación JWT con claims de rol (Espectador / Organizador)
- Renderizado JSON exclusivo (sin API browsable ni admin de Django)
- Templates y archivos estáticos de las vistas HTML
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SEGURIDAD Y HOSTS
# =============================================================================

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-clave-secreta-para-desarrollo-boletos-project-2026'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# =============================================================================
# APPS INSTALADAS
# NOTA: NO se instala django.contrib.admin (el sistema no usa el admin de Django)
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django_filters',
    'boletos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'boletos_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'boletos_project.wsgi.application'
ASGI_APPLICATION = 'boletos_project.asgi.application'

# =============================================================================
# BASE DE DATOS - POSTGRESQL (exigido por la rúbrica del proyecto)
# Configuración nativa con django.db.backends.postgresql.
# Variables de entorno: DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# DB_ENGINE=sqlite solo se usa como respaldo de desarrollo local (sin PostgreSQL).
# =============================================================================


def _configurar_base_de_datos():
    """Devuelve la configuración de la base de datos según las variables de entorno."""
    motor = os.environ.get('DB_ENGINE', 'postgresql').lower()

    if motor in ('sqlite', 'sqlite3'):
        # Respaldo local de desarrollo cuando no hay servidor PostgreSQL disponible.
        return {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

    # Motor PostgreSQL (configuración por defecto del proyecto).
    return {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'venta_entradas'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 5,
            },
        }
    }


DATABASES = _configurar_base_de_datos()

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# LOCALIZACIÓN
# =============================================================================

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
# Destino de collectstatic (servido por Nginx en el despliegue EC2)
STATIC_ROOT = BASE_DIR / 'static'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Modelo de usuario propio con campo de rol (Espectador / Organizador)
AUTH_USER_MODEL = 'boletos.User'

# =============================================================================
# DJANGO REST FRAMEWORK
# - Autenticación JWT (access + refresh) como único medio de escritura vía API.
# - Renderizado JSON exclusivo: NO existe vista HTML navegable del API.
# - Filtros (django-filter), búsqueda y ordenamiento habilitados por defecto.
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'boletos.pagination.ResultadosPaginados',
    'PAGE_SIZE': 20,
}

# =============================================================================
# DOCUMENTACIÓN DE LA API (Swagger / OpenAPI)
# El pie de página de cada pantalla enlaza a /docs/
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'API Venta de Entradas para Eventos y Conciertos',
    'DESCRIPTION': (
        'API de la plataforma de boletería para eventos masivos.\n\n'
        '**Alumno:** Benjamin Jaque  •  **Sección:** IEC-N4-C2  •  **Año:** 2026\n\n'
        'Roles: Espectador (carro de compras, pagos y entradas) y '
        'Organizador (eventos, sectores, ventas y cambio de estado de órdenes).\n\n'
        'Los endpoints públicos permiten consultar el catálogo; el resto requiere '
        'token JWT (Authorization: Bearer <access>) con el claim `rol`.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'name': 'Benjamin Jaque', 'email': ''},
    'LICENSE': {'name': 'IEC-N4-C2 - 2026'},
    # Nombres explícitos para los CHOICES que comparten el campo "estado"
    'ENUM_NAME_OVERRIDES': {
        'CompraEstadoEnum': 'boletos.models.Compra.Estado',
        'TicketEstadoEnum': 'boletos.models.Ticket.Estado',
        'EventoEstadoEnum': 'boletos.models.Evento.Estado',
        'EventoCategoriaEnum': 'boletos.models.Evento.Categoria',
        'UsuarioRolEnum': 'boletos.models.User.Rol',
    },
}

# =============================================================================
# JWT (access + refresh) CON CLAIM DE ROL
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    # Serializador propio: inyecta rol, nombre y banderas de rol en el payload.
    'TOKEN_OBTAIN_SERIALIZER': 'boletos.serializers.TokenConRolSerializer',
}

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'eventos'
LOGOUT_REDIRECT_URL = 'login'

# =============================================================================
# TRANSBANK WEBPAY PLUS (ambiente de integración / sandbox)
# Credenciales públicas de prueba publicadas por Transbank (no requieren
# cuenta real). Se pueden sobreescribir por variables de entorno para
# cambiar de ambiente (integración -> producción) sin tocar el código.
# =============================================================================

WEBPAY = {
    'BASE_URL': os.environ.get('WEBPAY_BASE_URL', 'https://webpay3gint.transbank.cl'),
    'CODIGO_COMERCIO': os.environ.get('WEBPAY_CODIGO_COMERCIO', '597055555532'),
    'API_KEY': os.environ.get(
        'WEBPAY_API_KEY',
        '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C',
    ),
    'TIMEOUT': int(os.environ.get('WEBPAY_TIMEOUT', '20')),
}
