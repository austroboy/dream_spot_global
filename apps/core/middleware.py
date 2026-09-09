"""Middleware: audit actor capture and maintenance mode (SRS FR-USR-03/04)."""
import threading
from django.shortcuts import render

_local = threading.local()


def get_current_user():
    return getattr(_local, "user", None)


def get_current_ip():
    return getattr(_local, "ip", None)


class AuditUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = getattr(request, "user", None)
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        _local.ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
        try:
            response = self.get_response(request)
        finally:
            _local.user = None
            _local.ip = None
        return response


class MaintenanceModeMiddleware:
    EXEMPT_PREFIXES = ("/dashboard/", "/django-admin/", "/accounts/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.core.models import SiteSettings
        if request.path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_staff:
            return self.get_response(request)
        try:
            settings_obj = SiteSettings.load()
        except Exception:
            return self.get_response(request)
        if settings_obj.maintenance_mode:
            return render(request, "core/maintenance.html",
                          {"settings_obj": settings_obj}, status=503)
        return self.get_response(request)
