from .base import *  # noqa

DEBUG = False

# Vercel injects VERCEL=1 into the runtime environment.
ON_VERCEL = bool(env("VERCEL")) or bool(env("VERCEL_URL"))

ALLOWED_HOSTS = [h for h in env("ALLOWED_HOSTS", "").split(",") if h]
if ON_VERCEL:
    ALLOWED_HOSTS += [".vercel.app", ".now.sh"]
    if env("VERCEL_URL"):
        ALLOWED_HOSTS.append(env("VERCEL_URL"))
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [".vercel.app"]

CSRF_TRUSTED_ORIGINS = [o for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
if ON_VERCEL:
    CSRF_TRUSTED_ORIGINS += ["https://*.vercel.app"]

# --- Security (SRS SEC-01) --------------------------------------------------
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not ON_VERCEL)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Static files -----------------------------------------------------------
# WhiteNoise serves collected static files straight from the application, which
# keeps the deployment working on hosts without a separate static file service.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Non-manifest storage: a missing hash entry can never 500 the whole site.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 31536000

# --- Media ------------------------------------------------------------------
# Serverless platforms give you a read-only filesystem apart from /tmp, so
# uploads survive only for the life of a single lambda instance. Point
# MEDIA_ROOT at /tmp there so uploads do not crash, and move to object storage
# (Vercel Blob, Cloudinary or S3) before real students upload documents.
if ON_VERCEL:
    MEDIA_ROOT = "/tmp/media"
    EPHEMERAL_MEDIA_WARNING = True

if env("REDIS_URL"):
    CACHES = {"default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }}
