"""Universities, courses, shortlist (SRS 6.3)."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import SEOFields, TimeStampedModel
from apps.core.utils import unique_slug

STUDY_LEVELS = [
    ("foundation", "Foundation"), ("diploma", "Diploma"), ("bachelor", "Bachelor's"),
    ("master", "Master's"), ("phd", "PhD"),
]
DISCIPLINES = [
    ("business", "Business & Management"), ("engineering", "Engineering & Technology"),
    ("it", "Computer Science & IT"), ("health", "Health & Medicine"),
    ("science", "Natural Sciences"), ("arts", "Arts & Humanities"),
    ("law", "Law"), ("social", "Social Sciences"), ("education", "Education"),
    ("hospitality", "Hospitality & Tourism"), ("agriculture", "Agriculture"),
]


class University(TimeStampedModel, SEOFields):
    TYPES = [("public", "Public"), ("private", "Private")]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    country = models.ForeignKey("destinations.Country", on_delete=models.PROTECT,
                                related_name="universities")   # SRS DM-03
    city = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="universities/logos/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="universities/cover/", blank=True, null=True)
    university_type = models.CharField(max_length=10, choices=TYPES, default="public")
    established_year = models.PositiveIntegerField(null=True, blank=True)

    world_ranking = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    national_ranking = models.PositiveIntegerField(null=True, blank=True)

    description = models.TextField(blank=True)
    accreditations = models.CharField(max_length=300, blank=True)
    facilities = models.TextField(blank=True, help_text="One item per line")

    tuition_min = models.PositiveIntegerField(null=True, blank=True)
    tuition_max = models.PositiveIntegerField(null=True, blank=True)
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    international_students = models.PositiveIntegerField(null=True, blank=True)
    website = models.URLField(blank=True)

    is_partner = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["world_ranking", "name"]
        verbose_name_plural = "Universities"
        indexes = [models.Index(fields=["country", "is_active"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("institutions:university_detail", args=[self.slug])

    def facility_items(self):
        return [ln.strip() for ln in (self.facilities or "").splitlines() if ln.strip()]

    def __str__(self):
        return self.name


class Course(TimeStampedModel, SEOFields):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    university = models.ForeignKey(University, on_delete=models.PROTECT,
                                   related_name="courses")     # SRS DM-06
    study_level = models.CharField(max_length=20, choices=STUDY_LEVELS, db_index=True)
    discipline = models.CharField(max_length=30, choices=DISCIPLINES, db_index=True)
    duration_months = models.PositiveIntegerField(default=12)
    tuition_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")     # SRS DM-07
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    overview = models.TextField(blank=True)
    entry_requirements = models.TextField(blank=True)
    english_requirements = models.TextField(blank=True)
    career_outcomes = models.TextField(blank=True)
    course_url = models.URLField(blank=True)

    intakes = models.ManyToManyField("destinations.Intake", blank=True, related_name="courses")
    scholarship_available = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["study_level", "discipline"]),
            models.Index(fields=["is_active", "university"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, f"{self.title}-{self.university.name}", max_length=250)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("institutions:course_detail", args=[self.slug])

    @property
    def country(self):
        return self.university.country

    @property
    def duration_display(self):
        y, m = divmod(self.duration_months, 12)
        parts = []
        if y:
            parts.append(f"{y} year{'s' if y > 1 else ''}")
        if m:
            parts.append(f"{m} month{'s' if m > 1 else ''}")
        return " ".join(parts) or "—"

    @property
    def tuition_display(self):
        return f"{self.currency} {self.tuition_fee:,.0f}" if self.tuition_fee else "On request"

    def __str__(self):
        return f"{self.title} — {self.university.name}"


class Shortlist(TimeStampedModel):
    """SRS FR-COU-07 — session shortlist merges into the account on login."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.CASCADE, related_name="shortlist")
    session_key = models.CharField(max_length=60, blank=True, db_index=True)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.CASCADE,
                               related_name="shortlisted_by")
    university = models.ForeignKey(University, null=True, blank=True, on_delete=models.CASCADE,
                                   related_name="shortlisted_by")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Shortlist: {self.course or self.university}"
