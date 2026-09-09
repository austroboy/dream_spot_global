"""Role-based access control helpers implementing the SRS §12.2 matrix."""
from functools import wraps

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.accounts.models import Role

# Capability -> roles allowed. Mirrors the SRS permission matrix exactly.
CAPABILITIES = {
    "view_all_leads":        {Role.ADMIN},
    "view_own_leads":        {Role.ADMIN, Role.COUNSELLOR},
    "edit_lead":             {Role.ADMIN, Role.COUNSELLOR},
    "reassign_leads":        {Role.ADMIN},
    "convert_lead":          {Role.ADMIN, Role.COUNSELLOR},
    "view_students":         {Role.ADMIN, Role.COUNSELLOR, Role.OFFICER},
    "edit_applications":     {Role.ADMIN, Role.COUNSELLOR, Role.OFFICER},
    "verify_documents":      {Role.ADMIN, Role.OFFICER},
    "manage_appointments":   {Role.ADMIN, Role.COUNSELLOR},
    "publish_content":       {Role.ADMIN, Role.EDITOR},
    "edit_catalogue":        {Role.ADMIN, Role.EDITOR},
    "manage_users":          {Role.ADMIN},
    "site_settings":         {Role.ADMIN},
    "view_reports":          {Role.ADMIN, Role.COUNSELLOR, Role.OFFICER},
    "view_all_reports":      {Role.ADMIN},
    "view_audit_log":        {Role.ADMIN},
}


def user_can(user, capability):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == Role.ADMIN:
        return True
    return user.role in CAPABILITIES.get(capability, set())


def require_capability(capability):
    """Decorator for function-based dashboard views."""
    def decorator(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if not user_can(request.user, capability):
                raise PermissionDenied("You do not have permission to perform this action.")
            return view(request, *args, **kwargs)
        return _wrapped
    return decorator


class CapabilityRequiredMixin(AccessMixin):
    """Mixin for class-based dashboard views."""
    capability = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.capability and not user_can(request.user, self.capability):
            raise PermissionDenied("You do not have permission to view this page.")
        return super().dispatch(request, *args, **kwargs)


class StaffRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff_member:
            raise PermissionDenied("Staff access only.")
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, "student_profile"):
            raise PermissionDenied("Student portal access only.")
        return super().dispatch(request, *args, **kwargs)
