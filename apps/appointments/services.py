"""Slot generation and booking (SRS FR-APT-01..07)."""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Role, StaffProfile
from apps.appointments.models import Appointment, Availability, BlackoutDate
from apps.notifications.services import notify_user, send_email

DAYS_AHEAD = 21


def counsellor_pool():
    return StaffProfile.objects.filter(user__role=Role.COUNSELLOR, user__is_active=True,
                                       is_available=True)


def available_slots(counsellor=None, days=DAYS_AHEAD):
    """Return {date: [(iso_datetime, label, counsellor_id)]} for the next N days."""
    staff = [counsellor] if counsellor else list(counsellor_pool())
    if not staff:
        return {}
    staff_ids = [s.pk for s in staff]
    now = timezone.localtime()
    start_day = now.date()
    end_day = start_day + timedelta(days=days)

    taken = set(Appointment.objects.filter(
        counsellor_id__in=staff_ids, start_datetime__date__gte=start_day,
        status__in=["booked", "confirmed"]).values_list("counsellor_id", "start_datetime"))
    blackouts = set(BlackoutDate.objects.filter(counsellor_id__in=staff_ids)
                    .values_list("counsellor_id", "date"))

    rules = list(Availability.objects.filter(counsellor_id__in=staff_ids, is_active=True))
    calendar = {}
    day = start_day
    while day <= end_day:
        entries = []
        for rule in rules:
            if rule.weekday != day.weekday():
                continue
            if (rule.counsellor_id, day) in blackouts:
                continue
            for slot in rule.slots_for(day):
                if slot <= now + timedelta(hours=2):
                    continue
                if (rule.counsellor_id, slot) in taken:
                    continue
                entries.append({"iso": slot.isoformat(),
                                "label": timezone.localtime(slot).strftime("%I:%M %p").lstrip("0"),
                                "counsellor_id": rule.counsellor_id,
                                "counsellor": rule.counsellor.full_name})
        if entries:
            entries.sort(key=lambda e: e["iso"])
            calendar[day] = entries
        day += timedelta(days=1)
    return calendar


@transaction.atomic
def book(appointment, counsellor):
    """SRS FR-APT-03 — unique constraint prevents double booking."""
    appointment.counsellor = counsellor
    try:
        appointment.save()
    except IntegrityError:
        return None
    send_confirmation(appointment)
    if counsellor:
        notify_user(counsellor.user, f"New appointment: {appointment.full_name}",
                    body=timezone.localtime(appointment.start_datetime)
                         .strftime("%d %b %Y, %I:%M %p"),
                    level="info", url="/dashboard/appointments/")
    return appointment


def send_confirmation(appointment):
    """SRS FR-APT-04 — email with .ics attachment."""
    when = timezone.localtime(appointment.start_datetime).strftime("%A %d %B %Y, %I:%M %p")
    manage = f"/book-counselling/manage/{appointment.token}/"
    send_email(
        subject="Your free counselling session is confirmed — Dream Spot Global",
        to=appointment.email,
        body=(f"Dear {appointment.full_name},\n\nYour session is confirmed.\n\n"
              f"When: {when}\nMode: {appointment.get_mode_display()}\n"
              f"Counsellor: {appointment.counsellor.full_name if appointment.counsellor else 'To be assigned'}\n"
              f"Where: House 21, Road 01, Sector 9, Uttara, Dhaka\n\n"
              f"Reschedule or cancel: {manage}\n\nDream Spot Global"),
        attachments=[("appointment.ics", appointment.ics(), "text/calendar")])


def due_reminders():
    """SRS FR-APT-05 — called by the send_reminders management command."""
    now = timezone.now()
    out = []
    for appt in Appointment.objects.filter(status__in=["booked", "confirmed"],
                                           start_datetime__gt=now):
        delta = appt.start_datetime - now
        if not appt.reminder_24h_sent and delta <= timedelta(hours=24):
            out.append((appt, "24h"))
        elif not appt.reminder_2h_sent and delta <= timedelta(hours=2):
            out.append((appt, "2h"))
    return out
