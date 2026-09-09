from django.contrib import admin

from apps.applications.models import Application, ApplicationStageHistory, Document


class HistoryInline(admin.TabularInline):
    model = ApplicationStageHistory
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("reference_no", "student", "university", "stage", "visa_status",
                    "assigned_officer", "deadline")
    list_filter = ("stage", "visa_status", "university__country")
    search_fields = ("reference_no", "student__user__first_name", "student__user__email")
    inlines = [HistoryInline]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("student", "document_type", "status", "reviewed_by", "created_at")
    list_filter = ("status", "document_type")
