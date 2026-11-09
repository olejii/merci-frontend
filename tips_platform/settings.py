import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "tips",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "155.212.245.37:8080,"
        "https://tatarstaninnovation-llc-backend.vercel.app,"
        + os.environ.get("CSRF_TRUSTED_ORIGINS", "")
    ).split(",")
    if origin.strip()
]

ROOT_URLCONF = "tips_platform.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "tips_platform.wsgi.application"
ASGI_APPLICATION = "tips_platform.asgi.application"

sqlite_database = os.environ.get("TIP_DATABASE")
if sqlite_database:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_database,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("PG_DATABASE", "tatarstan_tips"),
            "USER": os.environ.get("PG_USER", "postgres"),
            "PASSWORD": os.environ.get("PG_PASSWORD", ""),
            "HOST": os.environ.get("PG_HOST", "localhost"),
            "PORT": os.environ.get("PG_PORT", "5432"),
            "OPTIONS": {
                "sslmode": os.environ.get("POSTGRES_SSLMODE", "require"),
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/admin/login/"

TIP_QR_SECRET = os.environ.get("TIP_QR_SECRET", "")
PUBLIC_BASE_URL = os.environ.get("h", "http://localhost:8000").rstrip("/")
QR_TTL_HOURS = 24
TIP_OPTIONS = [50, 100, 200, 500]
SERVICE_FEE_AMOUNT = "25.00"
