from django.contrib import admin

from apps.institutions.models import Course, Shortlist, University


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "city", "world_ranking", "is_partner", "is_active")
    list_filter = ("country", "university_type", "is_partner", "is_active")
    search_fields = ("name", "city")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "university", "study_level", "discipline", "tuition_fee",
                    "is_active")
    list_filter = ("study_level", "discipline", "is_active", "university__country")
    search_fields = ("title", "university__name")
    filter_horizontal = ("intakes",)


admin.site.register(Shortlist)
