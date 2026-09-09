from django.contrib import admin

from apps.testimonials.models import Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("student_name", "university", "country", "rating", "is_approved",
                    "is_featured")
    list_filter = ("is_approved", "is_featured", "country")
    list_editable = ("is_approved", "is_featured")
