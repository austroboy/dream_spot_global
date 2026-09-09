from django.contrib import admin

from apps.notifications.models import EmailTemplate, Message, MessageThread, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "title", "level", "is_read", "created_at")
    list_filter = ("level", "is_read")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "is_active")


admin.site.register([MessageThread, Message])
