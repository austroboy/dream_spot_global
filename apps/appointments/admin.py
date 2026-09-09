from django.contrib import admin

from apps.appointments.models import Appointment, Availability, BlackoutDate


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("counsellor", "weekday", "start_time", "end_time", "slot_minutes",
                    "is_active")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "start_datetime", "counsellor", "mode", "status")
    list_filter = ("status", "mode", "counsellor")
    search_fields = ("full_name", "email", "phone")


admin.site.register(BlackoutDate)
