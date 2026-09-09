from django.contrib import admin

from apps.core.models import (AuditLog, ContactMessage, HeroSlide, HomepageSection,
                              JourneyStep, Page, Redirect, SiteSettings, TeamMember,
                              WhyUsPoint)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "phone_primary", "email", "maintenance_mode")


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ("key", "heading", "is_active", "display_order")
    list_editable = ("is_active", "display_order")


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("heading", "is_active", "display_order")


@admin.register(WhyUsPoint)
class WhyUsPointAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "is_active")


@admin.register(JourneyStep)
class JourneyStepAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "is_active")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "display_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "show_in_footer")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("old_path", "new_path", "is_permanent")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model_name", "object_repr")
    list_filter = ("action", "model_name")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
