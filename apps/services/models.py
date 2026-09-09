"""The nine consultancy services (SRS 6.4)."""
from django.db import models
from django.urls import reverse

from apps.core.models import SEOFields, TimeStampedModel
from apps.core.utils import unique_slug


class Service(TimeStampedModel, SEOFields):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    icon = models.CharField(max_length=40, default="sparkles",
                            help_text="Lucide icon name (SRS UI-21)")
    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    whats_included = models.TextField(blank=True, help_text="One item per line")
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    related_countries = models.ManyToManyField("destinations.Country", blank=True,
                                               related_name="services")

    class Meta:
        ordering = ["display_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:detail", args=[self.slug])

    def included_items(self):
        return [ln.strip() for ln in (self.whats_included or "").splitlines() if ln.strip()]

    def __str__(self):
        return self.name


class ServiceStep(TimeStampedModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="steps")
    number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=160)
    description = models.CharField(max_length=400, blank=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"{self.service.name} — step {self.number}"
