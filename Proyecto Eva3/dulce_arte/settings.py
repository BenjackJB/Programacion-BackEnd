"""
Dulce Arte — Sistema de Trazabilidad y Pedidos para Pastelería Artesanal
Configuración de Django para EVA 3 · Desarrollo Backend.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables de un archivo .env si existe (desarrollo local y AWS).
# En producción también puede inyectarse desde systemd (EnvironmentFile=).
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def env(key: str, default: str = "") -> str:
    """Helper simple para leer variables de entorno con valor por defecto."""
    value = os.environ.get(key, default)
    return str(value)


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return str(raw).lower() in {"1", "true", "yes", "on"}


# Seguridad — en producción (AWS) se define SECRET_KEY y DEBUG en .env
SECRET_KEY = env(
    "SECRET_KEY",
    "django-insecure-cambie-esta-clave-en-produccion-eva3-dulce-arte",
)

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
if DEBUG:
    for extra in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"):
        if extra not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(extra)

# IP pública / DNS (DuckDNS) de la instancia EC2 — se inyecta desde .env
_public_host = env("PUBLIC_HOST", "")
if _public_host and _public_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_public_host)

CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    if host and not host.startswith("["):
        CSRF_TRUSTED_ORIGINS.append(f"http://{host}")
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "rest_framework.authtoken",
    "core",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dulce_arte.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.rol_usuario",
            ],
        },
    },
]

WSGI_APPLICATION = "dulce_arte.wsgi.application"

# ---------------------------------------------------------------------------
# Base de datos: PostgreSQL en AWS EC2 · SQLite como respaldo en local.
# La configuración se lee desde DATABASE_URL (postgres://user:pass@host:5432/db)
# o desde las variables PG* individuales.
# ---------------------------------------------------------------------------
DATABASE_URL = env("DATABASE_URL", "")

if DATABASE_URL:
    _parsed = urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _parsed.path.lstrip("/") or "dulce_arte",
            "USER": _parsed.username or "dulce",
            "PASSWORD": _parsed.password or "",
            "HOST": _parsed.hostname or "localhost",
            "PORT": str(_parsed.port or 5432),
            "CONN_MAX_AGE": 60,
        }
    }
elif env("PGDATABASE", ""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("PGDATABASE"),
            "USER": env("PGUSER", "dulce"),
            "PASSWORD": env("PGPASSWORD", ""),
            "HOST": env("PGHOST", "localhost"),
            "PORT": env("PGPORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos (CSS/JS) — servidos por Nginx en producción
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Sesiones
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 días
SESSION_SAVE_EVERY_REQUEST = True

# URL de redirección tras login
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# Mensajes
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
