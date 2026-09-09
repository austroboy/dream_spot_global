from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.utils import capture_utm
from apps.events.forms import EventRegistrationForm
from apps.events.models import Event
from apps.leads.services import create_lead
from apps.notifications.services import send_email


def event_list(request):
    tab = request.GET.get("tab", "upcoming")
    base = Event.objects.filter(status="published").prefetch_related("countries")
    if tab == "past":
        qs = base.filter(start_datetime__lt=timezone.now()).order_by("-start_datetime")
    else:
        qs = base.filter(start_datetime__gte=timezone.now()).order_by("start_datetime")
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "events/list.html", {
        "page_obj": page, "tab": tab,
        "meta_title": "Education Fairs & Webinars | Dream Spot Global",
    })


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.prefetch_related("universities", "countries"), slug=slug,
        status="published")
    form = EventRegistrationForm(request.POST or None)
    if request.method == "POST":
        if not event.registration_open:
            messages.error(request, "Registration for this event is closed.")
            return redirect(event.get_absolute_url())
        if form.is_valid():
            reg = form.save(commit=False)
            reg.event = event
            reg.status = "waitlist" if event.is_full else "confirmed"   # SRS FR-EVT-03
            lead, _ = create_lead(
                data={"full_name": reg.full_name, "email": reg.email, "phone": reg.phone,
                      "study_level": reg.study_level or "", "consent_given": True,
                      "message": f"Registered for event: {event.title}"},
                destinations=[reg.destination_interest] if reg.destination_interest else None,
                meta=capture_utm(request), source="event")
            reg.lead = lead
            reg.save()
            send_email(
                subject=f"Registration confirmed — {event.title}",
                to=reg.email,
                body=(f"Dear {reg.full_name},\n\nYour place at {event.title} is "
                      f"{reg.get_status_display().lower()}.\n"
                      f"When: {timezone.localtime(event.start_datetime):%d %b %Y, %I:%M %p}\n"
                      f"Where: {event.online_link or event.venue}\n\nDream Spot Global"))
            messages.success(request, "You are registered. Check your email for details.")
            return redirect(event.get_absolute_url())
    return render(request, "events/detail.html", {
        "event": event, "form": form,
        "meta_title": event.meta_title or event.title,
    })
