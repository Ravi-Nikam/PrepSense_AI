from .settings import *  # noqa: F401,F403
from .settings import INSTALLED_APPS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = INSTALLED_APPS + ["tests_support"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False  # eager task errors don't bubble into the request
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

TENANT_STRICT = True

LLM_PROVIDER = "fake"
EMBEDDING_PROVIDER = "fake"

SECRET_KEY = "test-secret-key-that-is-comfortably-long-enough-for-hs256-signing"

# Deterministic password hashing => faster tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
