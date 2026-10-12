import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "synthetic-local-development-only-change-before-hosting"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "true") == "true"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "navigation",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "care_navigator"),
        "USER": os.environ.get("PGUSER", "agent"),
        "PASSWORD": os.environ.get("PGPASSWORD", ""),
        "HOST": os.environ.get("PGHOST", "/workspace/care-navigator-runtime"),
        "PORT": os.environ.get("PGPORT", "5432"),
    }
}
ROOT_URLCONF = "config.urls"
USE_TZ = True
TIME_ZONE = "America/Los_Angeles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 28800
SECURE_CONTENT_TYPE_NOSNIFF = True
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
VERIFICATION_STALE_DAYS = int(os.environ.get("VERIFICATION_STALE_DAYS", "30"))
EMERGENCY_INSTRUCTIONS = os.environ.get(
    "EMERGENCY_INSTRUCTIONS",
    "If you think you have an emergency, contact local emergency services. Prototype wording awaits clinical review. This app is not monitored for emergencies.",
)

CSRF_TRUSTED_ORIGINS = (
    ["http://127.0.0.1:5173", "http://localhost:5173"] if DEBUG else []
)
