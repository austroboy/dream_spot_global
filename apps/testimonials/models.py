"""Success stories (SRS 6.11)."""
from django.db import models

from apps.core.models import TimeStampedModel


class Testimonial(TimeStampedModel):
    student_name = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    country = models.ForeignKey("destinations.Country", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="testimonials")
    university = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=200, blank=True)
    intake_year = models.PositiveIntegerField(null=True, blank=True)
    quote = models.CharField(max_length=400)
    story = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    video_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False, db_index=True)   # SRS FR-TST-02

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def stars(self):
        return range(self.rating)

    def __str__(self):
        return f"{self.student_name} — {self.university}"
