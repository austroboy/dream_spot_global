from django.contrib import admin

from apps.events.models import Event, EventRegistration


class RegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "start_datetime", "capacity", "status")
    list_filter = ("event_type", "status")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("universities", "countries")
    inlines = [RegistrationInline]


admin.site.register(EventRegistration)
