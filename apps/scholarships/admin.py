from django.contrib import admin

from apps.scholarships.models import Scholarship


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "award_type", "application_deadline", "is_active")
    list_filter = ("country", "award_type", "is_active")
    search_fields = ("title", "provider")
    prepopulated_fields = {"slug": ("title",)}
