"""Sidebar navigation filtered by the signed-in user's capabilities (SRS 12.2)."""
from apps.accounts.permissions import user_can
from apps.dashboard.forms import CONTENT_MODELS


def dashboard_nav(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not getattr(user, "is_staff_member", False):
        return {}
    nav = [(key, cfg) for key, cfg in CONTENT_MODELS.items()
           if user_can(user, cfg["capability"])]
    return {
        "content_nav": nav,
        "perms_view_reports": user_can(user, "view_reports"),
    }
