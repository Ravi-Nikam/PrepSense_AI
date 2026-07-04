from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    TENANT_STRICT=(bool, True),
    JWT_ACCESS_TOKEN_LIFETIME_MIN=(int, 30),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    EMBEDDING_DIM=(int, 1024),
    LLM_DAILY_CALL_CAP_PER_TENANT=(int, 500),
    LLM_MONTHLY_CALL_CAP_PER_TENANT=(int, 10000),
    ANTHROPIC_MODEL=(str, "claude-sonnet-5"),
    ANTHROPIC_EMBEDDING_MODEL=(str, "voyage-3"),
    ANTHROPIC_API_KEY=(str, ""),
    # Google Gemini (free-tier friendly alternative to Anthropic).
    GEMINI_MODEL=(str, "gemini-2.5-flash"),
    GEMINI_API_KEY=(str, ""),
    LLM_PROVIDER=(str, "fake"),          # fake | anthropic | gemini
    EMBEDDING_PROVIDER=(str, "fake"),    # fake | voyage
    VOYAGE_API_KEY=(str, ""),
)

# Load .env if present (does nothing in prod where real env vars are set).
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
# Comma-separated https origins for CSRF (e.g. https://app.example.com).
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    # Local apps (one per bounded concern)
    "core",       # shared helpers: pagination, permissions, filters, constants
    "tenants",    # Organization (tenant) + isolation core
    "accounts",   # custom User + auth/RBAC
    "materials",  # SourceMaterial + MaterialChunk (EXAM/INTERVIEW source)
    "questions",  # Question (grounded, mode-tagged)
    "attempts",   # Attempt (answer + grade)
    "reports",    # progress aggregation + observer dashboards
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.RequestLoggingMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "tenants.middleware.CurrentTenantMiddleware",
]

ROOT_URLCONF = "prepcheck.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "prepcheck.wsgi.application"
ASGI_APPLICATION = "prepcheck.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DJANGO_DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Consistent, structured error responses (no leaked stack traces).
    "EXCEPTION_HANDLER": "prepcheck.exceptions.structured_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": env("USER_THROTTLE_RATE", default="1000/min"),
        "anon": env("ANON_THROTTLE_RATE", default="60/min"),
        "login": env("LOGIN_THROTTLE_RATE", default="10/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MIN")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "PrepCheck API",
    "DESCRIPTION": "Multi-tenant exam & interview preparation platform.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL")
ANTHROPIC_EMBEDDING_MODEL = env("ANTHROPIC_EMBEDDING_MODEL")
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL")
EMBEDDING_DIM = env("EMBEDDING_DIM")
LLM_PROVIDER = env("LLM_PROVIDER")
EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER")
VOYAGE_API_KEY = env("VOYAGE_API_KEY")

# Per-tenant LLM cost caps (enforced by the throttle class).
LLM_DAILY_CALL_CAP_PER_TENANT = env("LLM_DAILY_CALL_CAP_PER_TENANT")
LLM_MONTHLY_CALL_CAP_PER_TENANT = env("LLM_MONTHLY_CALL_CAP_PER_TENANT")

TENANT_STRICT = env("TENANT_STRICT")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"

LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")
LOG_FILE = env("DJANGO_LOG_FILE", default="")  # set a path to also log to a rotating file

_log_handlers = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "structured",
        "filters": ["tenant_context"],
    },
}
if LOG_FILE:
    _log_handlers["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_FILE,
        "maxBytes": 10 * 1024 * 1024,
        "backupCount": 5,
        "formatter": "structured",
        "filters": ["tenant_context"],
    }
_handler_names = list(_log_handlers)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s "
                "req=%(request_id)s tenant=%(tenant)s user=%(user)s %(message)s"
            ),
        },
    },
    "filters": {
        "tenant_context": {"()": "tenants.logging.TenantContextFilter"},
    },
    "handlers": _log_handlers,
    "root": {"handlers": _handler_names, "level": LOG_LEVEL},
    "loggers": {
        "prepcheck": {"handlers": _handler_names, "level": LOG_LEVEL, "propagate": False},
        # Django's own request warnings (4xx/5xx) with the same structured format.
        "django.request": {"handlers": _handler_names, "level": "WARNING", "propagate": False},
    },
}
