"""Education fairs, seminars, webinars (SRS 6.9)."""
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import SEOFields, TimeStampedModel
from apps.core.utils import unique_slug


class Event(TimeStampedModel, SEOFields):
    TYPES = [("fair", "Education fair"), ("seminar", "Seminar"),
             ("webinar", "Webinar"), ("visit", "University visit")]
    STATUS = [("draft", "Draft"), ("published", "Published"), ("cancelled", "Cancelled")]

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    event_type = models.CharField(max_length=12, choices=TYPES, default="fair")
    description = models.TextField(blank=True)
    banner = models.ImageField(upload_to="events/", blank=True, null=True)

    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=255, blank=True)
    online_link = models.URLField(blank=True)
    is_online = models.BooleanField(default=False)

    universities = models.ManyToManyField("institutions.University", blank=True,
                                          related_name="events")
    countries = models.ManyToManyField("destinations.Country", blank=True, related_name="events")
    capacity = models.PositiveIntegerField(default=100)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft", db_index=True)

    class Meta:
        ordering = ["start_datetime"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, max_length=240)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.slug])

    @property
    def is_past(self):
        return self.start_datetime < timezone.now()

    @property
    def seats_taken(self):
        return self.registrations.filter(status__in=["confirmed", "attended"]).count()

    @property
    def seats_left(self):
        return max(0, self.capacity - self.seats_taken)

    @property
    def is_full(self):
        return self.seats_left == 0

    @property
    def registration_open(self):
        if self.status != "published" or self.is_past:
            return False
        if self.registration_deadline and self.registration_deadline < timezone.now():
            return False
        return True

    def __str__(self):
        return self.title


class EventRegistration(TimeStampedModel):
    STATUS = [("confirmed", "Confirmed"), ("waitlist", "Waitlisted"),
              ("attended", "Attended"), ("cancelled", "Cancelled")]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    full_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    destination_interest = models.ForeignKey("destinations.Country", null=True, blank=True,
                                             on_delete=models.SET_NULL, related_name="+")
    study_level = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="confirmed")
    attended = models.BooleanField(default=False)
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="event_registrations")

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("event", "email")]

    def __str__(self):
        return f"{self.full_name} — {self.event.title}"
