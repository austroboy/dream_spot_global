"""Shared helpers: slugs with redirects, unique refs, client IP (SRS URL-02)."""
import uuid

from django.utils.text import slugify


def unique_slug(instance, value, field_name="slug", max_length=200):
    base = slugify(value)[:max_length - 6] or uuid.uuid4().hex[:8]
    Model = instance.__class__
    slug = base
    n = 2
    qs = Model._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(**{field_name: slug}).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def device_type(request):
    ua = (request.META.get("HTTP_USER_AGENT") or "").lower()
    if any(k in ua for k in ("iphone", "android", "mobile")):
        return "mobile"
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    return "desktop"


def capture_utm(request):
    g = request.GET
    return {
        "utm_source": g.get("utm_source", "")[:80],
        "utm_medium": g.get("utm_medium", "")[:80],
        "utm_campaign": g.get("utm_campaign", "")[:120],
        "referrer": (request.META.get("HTTP_REFERER") or "")[:300],
        "source_page": request.path[:255],
        "device": device_type(request),
        "ip_address": client_ip(request),
    }
