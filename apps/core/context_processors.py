"""Template context available on every page (SRS CON-05)."""
from django.core.cache import cache

from apps.core.models import SiteSettings


def site_settings(request):
    obj = cache.get("site_settings")
    if obj is None:
        try:
            obj = SiteSettings.load()
            cache.set("site_settings", obj, 300)
        except Exception:
            obj = None
    return {"site": obj}


def global_nav(request):
    """Navigation data for the mega-menu (SRS UI-03), cached for 10 minutes."""
    data = cache.get("global_nav")
    if data is None:
        from apps.destinations.models import Country
        from apps.services.models import Service
        data = {
            "nav_countries": list(Country.objects.filter(is_active=True)[:12]),
            "nav_services": list(Service.objects.filter(is_active=True)[:12]),
        }
        cache.set("global_nav", data, 600)
    return data
