"""Base settings shared by all environments (SRS NFR-M-03)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    v = os.environ.get(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("SECRET_KEY", "dev-insecure-change-me-in-production")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [h for h in env("ALLOWED_HOSTS", "*").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    # Dream Spot Global apps
    "apps.accounts",
    "apps.core",
    "apps.destinations",
    "apps.institutions",
    "apps.services",
    "apps.scholarships",
    "apps.leads",
    "apps.applications",
    "apps.appointments",
    "apps.blog",
    "apps.events",
    "apps.testimonials",
    "apps.faqs",
    "apps.notifications",
    "apps.dashboard",
    "apps.portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.AuditUserMiddleware",
    "apps.core.middleware.MaintenanceModeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
                "apps.core.context_processors.global_nav",
                "apps.notifications.context_processors.unread_notifications",
                "apps.dashboard.context_processors.dashboard_nav",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database (SRS 2.5) -----------------------------------------------------
def _database_from_url(url):
    """Parse a DATABASE_URL into Django config.

    Supports PostgreSQL (Neon, Supabase, Railway, Heroku) and MySQL / MariaDB
    (cPanel shared hosting), so the same codebase deploys to either.
    """
    from urllib.parse import parse_qs, unquote, urlparse

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    scheme = parsed.scheme.split("+")[0].lower()
    is_mysql = scheme in ("mysql", "mariadb")

    options = {}
    if is_mysql:
        options["charset"] = query.get("charset", ["utf8mb4"])[0]
        # Fail loudly on bad data instead of silently truncating it
        options["init_command"] = "SET sql_mode='STRICT_TRANS_TABLES'"
        if query.get("ssl") == ["true"]:
            options["ssl"] = {"ssl_mode": "REQUIRED"}
    else:
        sslmode = query.get("sslmode", ["require"])[0]
        if sslmode:
            options["sslmode"] = sslmode
        if query.get("channel_binding"):
            options["channel_binding"] = query["channel_binding"][0]

    config = {
        "ENGINE": "django.db.backends.mysql" if is_mysql
                  else "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        # Some hosts expose MySQL only over a unix socket; Django treats a HOST
        # beginning with "/" as a socket path.
        "HOST": (query.get("unix_socket", [""])[0] or parsed.hostname
                 or ("localhost" if is_mysql else "")),
        "PORT": str(parsed.port or (3306 if is_mysql else 5432)),
        "CONN_MAX_AGE": int(env("CONN_MAX_AGE", "60" if is_mysql else "0")),
        "OPTIONS": options,
    }
    if is_mysql:
        # Used only when running the test suite
        config["TEST"] = {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"}
    return config


if env("DATABASE_URL"):
    DATABASES = {"default": _database_from_url(env("DATABASE_URL"))}
elif env("MYSQL_DB"):
    DATABASES = {"default": _database_from_url(
        "mysql://{user}:{pw}@{host}:{port}/{name}".format(
            user=env("MYSQL_USER", ""), pw=env("MYSQL_PASSWORD", ""),
            host=env("MYSQL_HOST", "localhost"), port=env("MYSQL_PORT", "3306"),
            name=env("MYSQL_DB")))}
elif env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER", "postgres"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
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

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailOrUsernameBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"          # SRS FR-APT-07
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/portal/"
LOGOUT_REDIRECT_URL = "/"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14      # SRS SEC-06 (students)
STAFF_SESSION_COOKIE_AGE = 60 * 60 * 8      # SRS SEC-06 (staff)
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# --- File upload rules (SRS FR-STU-06) --------------------------------------
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".docx"]
ALLOWED_UPLOAD_MIME = [
    "application/pdf", "image/jpeg", "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

# --- Email (SRS INT-01) -----------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Dream Spot Global <dreamspotglobal@gmail.com>")
NOTIFY_EMAILS = [e for e in env("NOTIFY_EMAILS", "dreamspotglobal@gmail.com").split(",") if e]

# --- Third party keys (SRS INT-12) ------------------------------------------
RECAPTCHA_SITE_KEY = env("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = env("RECAPTCHA_SECRET_KEY", "")
GA4_MEASUREMENT_ID = env("GA4_MEASUREMENT_ID", "")
GTM_ID = env("GTM_ID", "")
META_PIXEL_ID = env("META_PIXEL_ID", "")
SMS_API_KEY = env("SMS_API_KEY", "")
SMS_SENDER_ID = env("SMS_SENDER_ID", "DreamSpot")

# --- Business rules ---------------------------------------------------------
LEAD_DUPLICATE_WINDOW_DAYS = 30      # SRS FR-LED-07
LEAD_OVERDUE_DAYS = 3                # SRS FR-LDM-09
LEAD_RATE_LIMIT_PER_HOUR = 5         # SRS FR-LED-05
LEAD_DATA_RETENTION_YEARS = 3        # SRS PRV-05

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
