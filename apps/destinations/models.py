"""Destination countries and guides (SRS 6.2)."""
from django.db import models
from django.urls import reverse

from apps.core.models import SEOFields, TimeStampedModel
from apps.core.utils import unique_slug


class Country(TimeStampedModel, SEOFields):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    code = models.CharField(max_length=3, blank=True)
    flag = models.ImageField(upload_to="countries/flags/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="countries/hero/", blank=True, null=True)
    card_image = models.ImageField(upload_to="countries/card/", blank=True, null=True)
    currency = models.CharField(max_length=8, default="USD")

    tagline = models.CharField(max_length=180, blank=True)
    overview = models.TextField(blank=True)
    why_study = models.TextField(blank=True)
    education_system = models.TextField(blank=True)
    admission_requirements = models.TextField(blank=True)
    english_requirements = models.TextField(blank=True)
    visa_process = models.TextField(blank=True)
    post_study_work = models.TextField(blank=True)
    part_time_work = models.TextField(blank=True)

    tuition_min = models.PositiveIntegerField(null=True, blank=True)
    tuition_max = models.PositiveIntegerField(null=True, blank=True)
    living_cost_min = models.PositiveIntegerField(null=True, blank=True)
    living_cost_max = models.PositiveIntegerField(null=True, blank=True)
    visa_duration = models.CharField(max_length=80, blank=True)
    work_hours_allowed = models.CharField(max_length=80, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Countries"

    def save(self, *args, **kwargs):
        old_slug = None
        if self.pk:
            old_slug = Country.objects.filter(pk=self.pk).values_list("slug", flat=True).first()
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)
        if old_slug and old_slug != self.slug:      # SRS URL-02
            from apps.core.models import Redirect
            Redirect.objects.get_or_create(
                old_path=f"/study-abroad/{old_slug}/",
                defaults={"new_path": self.get_absolute_url()})

    def get_absolute_url(self):
        return reverse("destinations:detail", args=[self.slug])

    def __str__(self):
        return self.name

    @property
    def tuition_range(self):
        if self.tuition_min and self.tuition_max:
            return f"{self.currency} {self.tuition_min:,} – {self.tuition_max:,} / year"
        return "On request"

    @property
    def living_range(self):
        if self.living_cost_min and self.living_cost_max:
            return f"{self.currency} {self.living_cost_min:,} – {self.living_cost_max:,} / month"
        return "On request"


class Intake(TimeStampedModel):
    """SRS FR-DST-05."""
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="intakes")
    name = models.CharField(max_length=60)
    months = models.CharField(max_length=80, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["application_deadline", "name"]
        unique_together = [("country", "name")]

    def __str__(self):
        return f"{self.country.name} — {self.name}"


class CostOfLiving(TimeStampedModel):
    """SRS FR-DST-03 — structured monthly cost breakdown."""
    CATEGORIES = [("accommodation", "Accommodation"), ("food", "Food"),
                  ("transport", "Transport"), ("utilities", "Utilities"),
                  ("miscellaneous", "Miscellaneous")]
    country = models.OneToOneField(Country, on_delete=models.CASCADE, related_name="cost")
    accommodation_min = models.PositiveIntegerField(default=0)
    accommodation_max = models.PositiveIntegerField(default=0)
    food_min = models.PositiveIntegerField(default=0)
    food_max = models.PositiveIntegerField(default=0)
    transport_min = models.PositiveIntegerField(default=0)
    transport_max = models.PositiveIntegerField(default=0)
    utilities_min = models.PositiveIntegerField(default=0)
    utilities_max = models.PositiveIntegerField(default=0)
    misc_min = models.PositiveIntegerField(default=0)
    misc_max = models.PositiveIntegerField(default=0)
    bdt_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                   help_text="1 unit of local currency in BDT")

    class Meta:
        verbose_name_plural = "Cost of living"

    def __str__(self):
        return f"Cost of living — {self.country.name}"

    def rows(self):
        data = [
            ("Accommodation", self.accommodation_min, self.accommodation_max),
            ("Food", self.food_min, self.food_max),
            ("Transport", self.transport_min, self.transport_max),
            ("Utilities", self.utilities_min, self.utilities_max),
            ("Miscellaneous", self.misc_min, self.misc_max),
        ]
        out = []
        for label, lo, hi in data:
            out.append({
                "label": label, "low": lo, "high": hi,
                "bdt_low": int(lo * self.bdt_rate), "bdt_high": int(hi * self.bdt_rate),
            })
        return out

    def totals(self):
        lo = sum(r["low"] for r in self.rows())
        hi = sum(r["high"] for r in self.rows())
        return {"low": lo, "high": hi,
                "bdt_low": int(lo * self.bdt_rate), "bdt_high": int(hi * self.bdt_rate)}


class VisaRequirement(TimeStampedModel):
    """SRS FR-DST-02 — visa checklist items."""
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="visa_items")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.country.name}: {self.title}"
