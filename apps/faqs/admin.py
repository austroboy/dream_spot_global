from django.contrib import admin

from apps.faqs.models import FAQ, FAQCategory


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "show_on_homepage", "is_active", "display_order")
    list_filter = ("category", "is_active", "show_on_homepage")


admin.site.register(FAQCategory)
