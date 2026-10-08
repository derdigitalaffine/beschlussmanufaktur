import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY benötigt mindestens 50 Zeichen.")
DEBUG = False
SERVER_ROLE = os.environ.get("SERVER_ROLE", "internal")
if SERVER_ROLE not in {"internal", "protected", "public"}:
    raise ImproperlyConfigured("Ungültige SERVER_ROLE.")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
if "127.0.0.1" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("127.0.0.1")  # Private container readiness probe.
CSRF_TRUSTED_ORIGINS = list(filter(None, os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")))
APPLICATION_URL = os.environ.get("APPLICATION_URL", "https://localhost").rstrip("/")
application_url = urlparse(APPLICATION_URL)
if application_url.scheme != "https" or not application_url.hostname or application_url.username or application_url.password or application_url.path or application_url.query or application_url.fragment:
    raise ImproperlyConfigured("APPLICATION_URL muss ein vollständiger HTTPS-Origin ohne Pfad sein.")
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "core.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "core.middleware.FactorVersionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "core.portal_configuration.context_processor",
    ]},
}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql", "NAME": os.environ.get("POSTGRES_DB", "beschlussmanufaktur"),
    "USER": os.environ.get("POSTGRES_USER", "beschlussmanufaktur"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
    "HOST": os.environ.get("POSTGRES_HOST", "db"), "PORT": "5432", "CONN_MAX_AGE": 60,
}}
AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = BASE_DIR / "data"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/anmelden/"
SESSION_COOKIE_NAME = f"bm_{SERVER_ROLE}_session"
CSRF_COOKIE_NAME = f"bm_{SERVER_ROLE}_csrf"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 8 * 60 * 60
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true"
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/"]
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("SMTP_HOST", "")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("SMTP_STARTTLS", "true").lower() == "true"
EMAIL_USE_SSL = os.environ.get("SMTP_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get("SMTP_FROM", "")
# Different signing keys for the protected and public channels. Empty disables transfer.
EXCHANGE_SOURCE = os.environ.get('EXCHANGE_SOURCE', '')
EXCHANGE_PROTECTED_KEY = os.environ.get('EXCHANGE_PROTECTED_KEY', '')
EXCHANGE_PUBLIC_KEY = os.environ.get('EXCHANGE_PUBLIC_KEY', '')
EXCHANGE_PROTECTED_URL = os.environ.get('EXCHANGE_PROTECTED_URL', '')
EXCHANGE_PUBLIC_URL = os.environ.get('EXCHANGE_PUBLIC_URL', '')
EXCHANGE_CA_FILE = os.environ.get('EXCHANGE_CA_FILE', '')
EXCHANGE_MAX_AGE = int(os.environ.get('EXCHANGE_MAX_AGE', '86400'))
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
