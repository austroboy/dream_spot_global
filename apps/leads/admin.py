from django.contrib import admin

from apps.leads.models import Lead, LeadActivity, LeadNote, NewsletterSubscriber


class ActivityInline(admin.TabularInline):
    model = LeadActivity
    extra = 0
    readonly_fields = ("created_at",)


class NoteInline(admin.TabularInline):
    model = LeadNote
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email", "status", "source", "assigned_to",
                    "created_at")
    list_filter = ("status", "source", "assigned_to", "is_deleted")
    search_fields = ("full_name", "email", "phone")
    filter_horizontal = ("destinations",)
    inlines = [ActivityInline, NoteInline]


admin.site.register([LeadActivity, LeadNote, NewsletterSubscriber])
