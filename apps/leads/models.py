"""Lead capture and lifecycle (SRS 6.6, 8.2, 9.2)."""
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimeStampedModel

STUDY_LEVELS = [("foundation", "Foundation"), ("diploma", "Diploma"),
                ("bachelor", "Bachelor's"), ("master", "Master's"), ("phd", "PhD")]
INTAKES = [("jan", "January"), ("may", "May / Summer"), ("sep", "September / Fall")]
ENGLISH_TESTS = [("none", "Not taken"), ("ielts", "IELTS"), ("pte", "PTE"),
                 ("toefl", "TOEFL"), ("duolingo", "Duolingo"), ("moi", "MOI")]


class LeadStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFIED = "qualified", "Qualified"
    SCHEDULED = "scheduled", "Counselling scheduled"
    CONVERTED = "converted", "Converted"
    NOT_INTERESTED = "not_interested", "Not interested"
    INVALID = "invalid", "Invalid"
    LOST = "lost", "Lost"


OPEN_STATUSES = [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED,
                 LeadStatus.SCHEDULED]

LEAD_SOURCES = [
    ("homepage_cta", "Homepage CTA"), ("contact", "Contact page"),
    ("service_page", "Service page"), ("destination_page", "Destination page"),
    ("course_page", "Course page"), ("scholarship_page", "Scholarship page"),
    ("assessment", "Free assessment"), ("appointment", "Counselling booking"),
    ("event", "Event registration"), ("walk_in", "Walk-in"),
    ("facebook", "Facebook"), ("referral", "Referral"), ("other", "Other"),
]


class Lead(SoftDeleteModel):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    destinations = models.ManyToManyField("destinations.Country", blank=True,
                                          related_name="leads")
    study_level = models.CharField(max_length=20, choices=STUDY_LEVELS, blank=True)
    intended_intake = models.CharField(max_length=10, choices=INTAKES, blank=True)
    last_qualification = models.CharField(max_length=160, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    english_test = models.CharField(max_length=12, choices=ENGLISH_TESTS, default="none")
    english_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    message = models.TextField(blank=True)

    # analytics / attribution (SRS FR-LED-03)
    source = models.CharField(max_length=30, choices=LEAD_SOURCES, default="other", db_index=True)
    source_page = models.CharField(max_length=255, blank=True)
    utm_source = models.CharField(max_length=80, blank=True)
    utm_medium = models.CharField(max_length=80, blank=True)
    utm_campaign = models.CharField(max_length=120, blank=True)
    referrer = models.CharField(max_length=300, blank=True)
    device = models.CharField(max_length=20, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=LeadStatus.choices,
                              default=LeadStatus.NEW, db_index=True)
    lost_reason = models.CharField(max_length=200, blank=True)
    priority = models.CharField(max_length=10, default="medium",
                                choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")])
    assigned_to = models.ForeignKey("accounts.StaffProfile", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="leads")
    next_follow_up = models.DateTimeField(null=True, blank=True, db_index=True)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    consent_given = models.BooleanField(default=True)   # SRS PRV-01
    consent_at = models.DateTimeField(null=True, blank=True)

    assessment_result = models.JSONField(default=dict, blank=True)   # SRS FR-ASM-04

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "assigned_to"]),
            models.Index(fields=["created_at", "source"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    @property
    def is_open(self):
        return self.status in OPEN_STATUSES

    @property
    def is_overdue(self):
        """SRS FR-LDM-09."""
        from django.conf import settings
        if not self.is_open:
            return False
        days = getattr(settings, "LEAD_OVERDUE_DAYS", 3)
        return self.last_activity_at < timezone.now() - timezone.timedelta(days=days)

    @property
    def destination_names(self):
        return ", ".join(c.name for c in self.destinations.all()) or "—"

    def touch(self):
        self.last_activity_at = timezone.now()
        self.save(update_fields=["last_activity_at", "updated_at"])


class LeadActivity(TimeStampedModel):
    """SRS FR-LDM-05 — immutable interaction timeline."""
    TYPES = [("created", "Created"), ("status_change", "Status change"),
             ("assigned", "Assigned"), ("call", "Call"), ("email", "Email"),
             ("whatsapp", "WhatsApp"), ("meeting", "Meeting"),
             ("enquiry", "Repeat enquiry"), ("converted", "Converted"),
             ("note", "Note")]
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=20, choices=TYPES, default="note")
    summary = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    actor = models.ForeignKey("accounts.User", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="lead_activities")

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Lead activities"

    def __str__(self):
        return f"{self.get_activity_type_display()}: {self.summary}"


class LeadNote(TimeStampedModel):
    """SRS FR-LDM-05 — append-only counsellor notes."""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
    body = models.TextField()
    author = models.ForeignKey("accounts.User", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="lead_notes")
    attachment = models.FileField(upload_to="leads/notes/", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.lead}"


class NewsletterSubscriber(TimeStampedModel):
    """SRS FR-NWS-01 — double opt-in."""
    email = models.EmailField(unique=True)
    is_confirmed = models.BooleanField(default=False)
    confirm_token = models.CharField(max_length=64, blank=True)
    unsubscribed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
