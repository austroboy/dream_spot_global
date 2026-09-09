"""Presentation helpers so templates stay logic-free (SRS 3.3)."""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def add_class(field, css):
    return field.as_widget(attrs={**field.field.widget.attrs, "class": css})


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return getattr(mapping, key, None)


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Rebuild the querystring, preserving filters while changing one key."""
    request = context.get("request")
    params = request.GET.copy() if request else {}
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    params.pop("page", None) if "page" not in kwargs else None
    return params.urlencode()


@register.simple_tag
def stars(rating):
    rating = int(rating or 0)
    return mark_safe("★" * rating + '<span style="color:#E3E8EF">' + "★" * (5 - rating)
                     + "</span>")


@register.filter
def initials(value):
    parts = [p for p in str(value or "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@register.filter
def status_class(status):
    return {
        "new": "info", "contacted": "info", "qualified": "warning",
        "scheduled": "warning", "converted": "success", "not_interested": "danger",
        "invalid": "danger", "lost": "danger",
        "pending": "warning", "verified": "success", "rejected": "danger",
        "reupload": "warning", "published": "success", "draft": "warning",
        "cancelled": "danger", "confirmed": "success", "booked": "info",
        "granted": "success", "refused": "danger", "waitlist": "warning",
        "attended": "success", "completed": "success", "no_show": "danger",
    }.get(str(status), "info")


@register.filter
def percentage(value, total):
    try:
        return round(float(value) / float(total) * 100)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def split_lines(value):
    return [ln.strip() for ln in str(value or "").splitlines() if ln.strip()]
