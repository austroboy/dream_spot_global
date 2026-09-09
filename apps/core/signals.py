"""Audit logging + cache invalidation signals (SRS FR-USR-04, FR-HOM-07)."""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.middleware import get_current_ip, get_current_user
from apps.core.models import AuditLog

AUDITED = {
    "Lead", "LeadNote", "LeadActivity", "Application", "ApplicationStageHistory",
    "StudentProfile", "Document", "Appointment", "University", "Course",
    "Country", "Scholarship", "Service", "BlogPost", "Event", "Testimonial",
    "SiteSettings", "User", "Page",
}
CACHE_BUSTERS = {"SiteSettings", "Country", "Service", "HomepageSection", "HeroSlide"}


def _serialise(instance):
    data = {}
    for f in instance._meta.fields:
        try:
            val = getattr(instance, f.attname)
            data[f.name] = str(val) if val is not None else None
        except Exception:
            continue
    return data


@receiver(pre_save)
def stamp_actor(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    user = get_current_user()
    if user is None or not getattr(user, "is_authenticated", False):
        return
    if hasattr(instance, "updated_by"):
        instance.updated_by = user
    if hasattr(instance, "created_by") and not instance.pk and instance.created_by_id is None:
        instance.created_by = user


@receiver(post_save)
def audit_save(sender, instance, created, **kwargs):
    if kwargs.get("raw"):        # loaddata / fixtures — skip auditing
        return
    name = sender.__name__
    if name in CACHE_BUSTERS:
        cache.delete_many(["site_settings", "global_nav", "homepage"])
    if name not in AUDITED:
        return
    user = get_current_user()
    AuditLog.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        action="create" if created else "update",
        model_name=name,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=_serialise(instance) if created else {},
        ip_address=get_current_ip(),
    )


@receiver(post_delete)
def audit_delete(sender, instance, **kwargs):
    name = sender.__name__
    if name in CACHE_BUSTERS:
        cache.delete_many(["site_settings", "global_nav", "homepage"])
    if name not in AUDITED:
        return
    user = get_current_user()
    AuditLog.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        action="delete", model_name=name, object_id=str(instance.pk),
        object_repr=str(instance)[:255], ip_address=get_current_ip(),
    )
