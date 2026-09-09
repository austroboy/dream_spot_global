"""Scholarships (SRS 6.5)."""
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import SEOFields, TimeStampedModel
from apps.core.utils import unique_slug


class Scholarship(TimeStampedModel, SEOFields):
    AWARD_TYPES = [("full", "Full scholarship"), ("partial", "Partial scholarship"),
                   ("tuition_waiver", "Tuition waiver"), ("stipend", "Stipend")]

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    provider = models.CharField(max_length=180, blank=True)
    country = models.ForeignKey("destinations.Country", on_delete=models.PROTECT,
                                related_name="scholarships")
    university = models.ForeignKey("institutions.University", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="scholarships")
    study_level = models.CharField(max_length=20, blank=True)
    award_type = models.CharField(max_length=20, choices=AWARD_TYPES, default="partial")
    award_amount = models.CharField(max_length=120, blank=True)
    currency = models.CharField(max_length=8, default="USD")

    eligibility = models.TextField(blank=True)
    required_documents = models.TextField(blank=True, help_text="One item per line")
    description = models.TextField(blank=True)
    official_link = models.URLField(blank=True)

    application_deadline = models.DateField(null=True, blank=True, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["application_deadline", "title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, max_length=240)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("scholarships:detail", args=[self.slug])

    @property
    def is_expired(self):
        return bool(self.application_deadline and self.application_deadline < timezone.localdate())

    @property
    def days_left(self):
        if not self.application_deadline:
            return None
        return (self.application_deadline - timezone.localdate()).days

    def document_items(self):
        return [ln.strip() for ln in (self.required_documents or "").splitlines() if ln.strip()]

    def __str__(self):
        return self.title
