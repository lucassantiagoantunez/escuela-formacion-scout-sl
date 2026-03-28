import os
from pathlib import Path

import dj_database_url


# ==================================================
# BLOQUE 1 - RUTA BASE DEL PROYECTO
# ==================================================
BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# BLOQUE 2 - SEGURIDAD Y MODO DESARROLLO
# ==================================================
SECRET_KEY = (
    os.getenv("DJANGO_SECRET_KEY")
    or os.getenv("SECRET_KEY")
    or "django-insecure-local-dev-key-change-me"
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes", "on")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if not DEBUG and SECRET_KEY == "django-insecure-local-dev-key-change-me":
    raise ValueError("Debes configurar DJANGO_SECRET_KEY o SECRET_KEY para producción.")


# ==================================================
# BLOQUE 3 - APLICACIONES INSTALADAS
# ==================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_ckeditor_5",
    "core",
]


# ==================================================
# BLOQUE 4 - MIDDLEWARE
# ==================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==================================================
# BLOQUE 5 - URLS Y APLICACIÓN WSGI / ASGI
# ==================================================
ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ==================================================
# BLOQUE 6 - TEMPLATES
# ==================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.paginas_menu",
            ],
        },
    },
]


# ==================================================
# BLOQUE 7 - BASE DE DATOS
# ==================================================
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


# ==================================================
# BLOQUE 8 - VALIDADORES DE CONTRASEÑA
# ==================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ==================================================
# BLOQUE 9 - IDIOMA Y ZONA HORARIA
# ==================================================
LANGUAGE_CODE = "es-ar"

TIME_ZONE = "America/Argentina/San_Luis"

USE_I18N = True
USE_TZ = True


# ==================================================
# BLOQUE 10 - ARCHIVOS ESTÁTICOS
# ==================================================
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# ==================================================
# BLOQUE 11 - ARCHIVOS SUBIDOS
# ==================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ==================================================
# BLOQUE 12 - CONFIGURACIÓN DE PROXY / HTTPS
# ==================================================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ==================================================
# BLOQUE 13 - CONFIGURACIÓN DE CKEDITOR 5
# ==================================================
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": {
            "items": [
                "heading", "|",
                "bold", "italic", "underline", "link", "|",
                "bulletedList", "numberedList", "|",
                "blockQuote", "insertTable", "|",
                "undo", "redo",
            ],
        },
        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
            ],
        },
    },
    "extends": {
        "toolbar": {
            "items": [
                "heading", "|",
                "bold", "italic", "underline", "link", "|",
                "bulletedList", "numberedList", "|",
                "blockQuote", "insertTable", "|",
                "undo", "redo",
            ],
        },
        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
            ],
        },
    },
}


# ==================================================
# BLOQUE 14 - CONFIGURACIÓN GENERAL DE DJANGO
# ==================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"