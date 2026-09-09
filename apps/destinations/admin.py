from django.contrib import admin

from apps.destinations.models import CostOfLiving, Country, Intake, VisaRequirement


class IntakeInline(admin.TabularInline):
    model = Intake
    extra = 0


class VisaInline(admin.TabularInline):
    model = VisaRequirement
    extra = 0


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "currency", "is_active", "is_featured", "display_order")
    list_editable = ("is_active", "is_featured", "display_order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [IntakeInline, VisaInline]


admin.site.register([CostOfLiving, Intake, VisaRequirement])
