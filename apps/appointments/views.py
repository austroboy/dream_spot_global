from datetime import datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import StaffProfile
from apps.appointments.forms import AppointmentForm
from apps.appointments.models import Appointment
from apps.appointments.services import available_slots, book, send_confirmation
from apps.core.utils import capture_utm
from apps.leads.services import create_lead


def book_view(request):
    form = AppointmentForm(request.POST or None)
    chosen_counsellor = None
    cid = request.GET.get("counsellor")
    if cid and cid.isdigit():
        chosen_counsellor = StaffProfile.objects.filter(pk=cid).first()

    if request.method == "POST" and form.is_valid():
        slot_raw = form.cleaned_data["slot"]
        start = parse_datetime(slot_raw)
        if start is None:
            messages.error(request, "Please choose a time slot.")
            return redirect("appointments:book")
        if timezone.is_naive(start):
            start = timezone.make_aware(start)
        counsellor = form.cleaned_data.get("counsellor")
        if counsellor is None:
            cal = available_slots()
            for entries in cal.values():
                for e in entries:
                    if e["iso"] == slot_raw:
                        counsellor = StaffProfile.objects.filter(
                            pk=e["counsellor_id"]).first()
                        break
                if counsellor:
                    break
        appt = form.save(commit=False)
        appt.start_datetime = start
        lead, _ = create_lead(
            data={"full_name": appt.full_name, "email": appt.email, "phone": appt.phone,
                  "message": appt.notes, "consent_given": True},
            destinations=[appt.destination] if appt.destination else None,
            meta=capture_utm(request), source="appointment")
        appt.lead = lead
        if request.user.is_authenticated and hasattr(request.user, "student_profile"):
            appt.student = request.user.student_profile
        saved = book(appt, counsellor)
        if saved is None:
            messages.error(request, "That slot was just taken. Please pick another time.")
            return redirect("appointments:book")
        messages.success(request, "Your free counselling session is booked. "
                                  "Check your email for the confirmation.")
        return redirect("appointments:success", token=saved.token)

    calendar = available_slots(chosen_counsellor)
    return render(request, "appointments/book.html", {
        "form": form, "calendar": calendar, "chosen_counsellor": chosen_counsellor,
        "meta_title": "Book Free Counselling | Dream Spot Global",
        "meta_description": "Book a free one-to-one counselling session with a Dream Spot "
                            "Global adviser in Uttara, Dhaka — in person, by phone or online.",
    })


def success(request, token):
    appt = get_object_or_404(Appointment, token=token)
    return render(request, "appointments/success.html", {
        "appointment": appt, "meta_title": "Appointment confirmed"})


def manage(request, token):
    """SRS FR-APT-06 — signed-token reschedule/cancel without login."""
    appt = get_object_or_404(Appointment, token=token)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "cancel":
            appt.status = "cancelled"
            appt.save(update_fields=["status", "updated_at"])
            messages.success(request, "Your appointment has been cancelled.")
            return redirect("core:home")
        if action == "reschedule":
            new_slot = parse_datetime(request.POST.get("slot", ""))
            if new_slot:
                if timezone.is_naive(new_slot):
                    new_slot = timezone.make_aware(new_slot)
                appt.start_datetime = new_slot
                appt.reminder_24h_sent = False
                appt.reminder_2h_sent = False
                appt.save()
                send_confirmation(appt)
                messages.success(request, "Your appointment has been rescheduled.")
                return redirect("appointments:success", token=appt.token)
            messages.error(request, "Please choose a new time slot.")
    return render(request, "appointments/manage.html", {
        "appointment": appt,
        "calendar": available_slots(appt.counsellor),
        "meta_title": "Manage your appointment",
    })


def ics_download(request, token):
    from django.http import HttpResponse
    appt = get_object_or_404(Appointment, token=token)
    resp = HttpResponse(appt.ics(), content_type="text/calendar")
    resp["Content-Disposition"] = 'attachment; filename="dreamspot-appointment.ics"'
    return resp
