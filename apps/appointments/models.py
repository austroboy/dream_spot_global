"""Counsellor availability and booking (SRS 6.8)."""
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

WEEKDAYS = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
            (4, "Friday"), (5, "Saturday"), (6, "Sunday")]


class Availability(TimeStampedModel):
    """SRS FR-APT-01."""
    counsellor = models.ForeignKey("accounts.StaffProfile", on_delete=models.CASCADE,
                                   related_name="availability")
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name_plural = "Availability"

    def __str__(self):
        return f"{self.counsellor.full_name} — {self.get_weekday_display()} " \
               f"{self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def slots_for(self, day):
        """Yield timezone-aware slot start datetimes for a given date."""
        tz = timezone.get_current_timezone()
        cursor = timezone.make_aware(datetime.combine(day, self.start_time), tz)
        end = timezone.make_aware(datetime.combine(day, self.end_time), tz)
        while cursor + timedelta(minutes=self.slot_minutes) <= end:
            yield cursor
            cursor += timedelta(minutes=self.slot_minutes)


class BlackoutDate(TimeStampedModel):
    counsellor = models.ForeignKey("accounts.StaffProfile", on_delete=models.CASCADE,
                                   related_name="blackouts")
    date = models.DateField()
    reason = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["date"]
        unique_together = [("counsellor", "date")]

    def __str__(self):
        return f"{self.counsellor.full_name} unavailable {self.date}"


class Appointment(TimeStampedModel):
    MODES = [("office", "In office"), ("phone", "Phone call"), ("online", "Online meeting")]
    STATUS = [("booked", "Booked"), ("confirmed", "Confirmed"), ("completed", "Completed"),
              ("cancelled", "Cancelled"), ("no_show", "No show")]

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)  # FR-APT-06
    counsellor = models.ForeignKey("accounts.StaffProfile", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="appointments")
    student = models.ForeignKey("accounts.StudentProfile", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="appointments")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="appointments")

    full_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    destination = models.ForeignKey("destinations.Country", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="appointments")
    mode = models.CharField(max_length=10, choices=MODES, default="office")
    start_datetime = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="booked", db_index=True)
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_2h_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_datetime"]
        constraints = [
            # SRS FR-APT-03 — database-level double-booking guard
            models.UniqueConstraint(fields=["counsellor", "start_datetime"],
                                    name="unique_counsellor_slot"),
        ]

    def __str__(self):
        return f"{self.full_name} — {self.start_datetime:%d %b %Y %H:%M}"

    @property
    def end_datetime(self):
        return self.start_datetime + timedelta(minutes=self.duration_minutes)

    @property
    def is_past(self):
        return self.start_datetime < timezone.now()

    def ics(self, site_name="Dream Spot Global"):
        """SRS FR-APT-04 — calendar attachment."""
        fmt = "%Y%m%dT%H%M%SZ"
        start = self.start_datetime.astimezone(dt_timezone.utc).strftime(fmt)
        end = self.end_datetime.astimezone(dt_timezone.utc).strftime(fmt)
        return "\r\n".join([
            "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{site_name}//EN",
            "BEGIN:VEVENT", f"UID:{self.token}@dreamspotglobal",
            f"DTSTAMP:{timezone.now().astimezone(dt_timezone.utc).strftime(fmt)}",
            f"DTSTART:{start}", f"DTEND:{end}",
            f"SUMMARY:Free counselling with {site_name}",
            f"DESCRIPTION:Mode: {self.get_mode_display()}",
            "END:VEVENT", "END:VCALENDAR",
        ])
