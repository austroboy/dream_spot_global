from django.contrib import admin

from apps.services.models import Service, ServiceStep


class StepInline(admin.TabularInline):
    model = ServiceStep
    extra = 0


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "is_active", "is_featured", "display_order")
    list_editable = ("is_active", "is_featured", "display_order")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("related_countries",)
    inlines = [StepInline]
