from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import AcademicRecord, LoginAttempt, StaffProfile, StudentProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "get_full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Dream Spot Global", {"fields": ("role", "phone", "avatar", "email_verified",
                                          "last_seen")}),
    )


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "designation", "is_available", "show_on_website")
    filter_horizontal = ("destinations_owned",)


class AcademicRecordInline(admin.TabularInline):
    model = AcademicRecord
    extra = 0


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "assigned_counsellor", "preferred_intake", "created_at")
    filter_horizontal = ("preferred_destinations",)
    inlines = [AcademicRecordInline]


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("identifier", "ip_address", "successful", "created_at")
    list_filter = ("successful",)
