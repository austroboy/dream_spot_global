"""Lead workflow services (SRS FR-LED-06/07, FR-LDM-04/06)."""
import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, StaffProfile, StudentProfile
from apps.core.validators import normalise_bd_phone
from apps.leads.models import Lead, LeadActivity, LeadStatus
from apps.notifications.services import notify_staff, notify_user, send_email

logger = logging.getLogger(__name__)


# --- Assignment (SRS FR-LDM-04) --------------------------------------------
def pick_counsellor(lead=None):
    from apps.core.models import SiteSettings
    mode = SiteSettings.load().lead_assignment_mode
    pool = StaffProfile.objects.filter(user__role=Role.COUNSELLOR, user__is_active=True,
                                       is_available=True)
    if not pool.exists():
        return None
    if mode == "manual":
        return None
    if mode == "by_country" and lead is not None:
        country_ids = list(lead.destinations.values_list("id", flat=True))
        if country_ids:
            owner = pool.filter(destinations_owned__in=country_ids).distinct().first()
            if owner:
                return owner
    # round robin: least open leads wins
    return sorted(pool, key=lambda s: s.open_lead_count())[0]


def find_duplicate(email, phone):
    """SRS FR-LED-07 — same phone or email inside the configured window."""
    window = timezone.now() - timezone.timedelta(days=settings.LEAD_DUPLICATE_WINDOW_DAYS)
    phone = normalise_bd_phone(phone)
    return Lead.objects.filter(created_at__gte=window).filter(
        models_q(email, phone)).order_by("-created_at").first()


def models_q(email, phone):
    from django.db.models import Q
    q = Q()
    if email:
        q |= Q(email__iexact=email)
    if phone:
        q |= Q(phone=phone)
    return q


@transaction.atomic
def create_lead(*, data, destinations=None, meta=None, source="other"):
    """Single entry point used by every public form (SRS FR-LED-01)."""
    meta = meta or {}
    phone = normalise_bd_phone(data.get("phone", ""))
    existing = find_duplicate(data.get("email"), phone)
    if existing:
        LeadActivity.objects.create(
            lead=existing, activity_type="enquiry",
            summary=f"Repeat enquiry from {meta.get('source_page', source)}",
            detail=data.get("message", ""))
        if destinations:
            existing.destinations.add(*destinations)
        existing.touch()
        _notify_new_lead(existing, repeat=True)
        return existing, False

    lead = Lead(
        full_name=data.get("full_name", "").strip(),
        email=data.get("email", "").strip().lower(),
        phone=phone,
        study_level=data.get("study_level", "") or "",
        intended_intake=data.get("intended_intake", "") or "",
        last_qualification=data.get("last_qualification", "") or "",
        gpa=data.get("gpa") or None,
        english_test=data.get("english_test") or "none",
        english_score=data.get("english_score") or None,
        message=data.get("message", "") or "",
        source=source,
        consent_given=bool(data.get("consent_given", True)),
        consent_at=timezone.now(),
        assessment_result=data.get("assessment_result") or {},
        **{k: v for k, v in meta.items() if k in {
            "source_page", "utm_source", "utm_medium", "utm_campaign",
            "referrer", "device", "ip_address"}},
    )
    lead.save()
    if destinations:
        lead.destinations.set(destinations)

    lead.assigned_to = pick_counsellor(lead)
    lead.save(update_fields=["assigned_to"])

    LeadActivity.objects.create(lead=lead, activity_type="created",
                                summary=f"Lead created from {lead.get_source_display()}")
    if lead.assigned_to:
        LeadActivity.objects.create(
            lead=lead, activity_type="assigned",
            summary=f"Auto-assigned to {lead.assigned_to.full_name}")
    _notify_new_lead(lead)
    return lead, True


def _notify_new_lead(lead, repeat=False):
    """SRS FR-LED-06 — student confirmation + internal alert."""
    prefix = "Repeat enquiry" if repeat else "New enquiry"
    send_email(
        subject="We have received your enquiry — Dream Spot Global",
        to=lead.email,
        template="emails/lead_confirmation.html",
        context={"lead": lead},
        body=(f"Dear {lead.full_name},\n\nThank you for contacting Dream Spot Global. "
              "One of our counsellors will contact you within one working day.\n\n"
              "Dream Spot Global — Education • Career • Immigration\n"
              "House 21, Road 01, Sector 9, Uttara, Dhaka"),
    )
    extra = [lead.assigned_to.user.email] if lead.assigned_to else []
    notify_staff(
        subject=f"{prefix}: {lead.full_name} ({lead.get_source_display()})",
        body=(f"Name: {lead.full_name}\nPhone: {lead.phone}\nEmail: {lead.email}\n"
              f"Destinations: {lead.destination_names}\nLevel: {lead.get_study_level_display()}\n"
              f"Message: {lead.message}\nSource page: {lead.source_page}"),
        extra_emails=extra)
    if lead.assigned_to:
        notify_user(lead.assigned_to.user, f"{prefix}: {lead.full_name}",
                    body=f"{lead.phone} • {lead.destination_names}",
                    level="warning", url=f"/dashboard/leads/{lead.pk}/")


def change_status(lead, new_status, actor=None, note=""):
    old = lead.get_status_display()
    lead.status = new_status
    lead.last_activity_at = timezone.now()
    lead.save(update_fields=["status", "last_activity_at", "updated_at"])
    LeadActivity.objects.create(lead=lead, activity_type="status_change", actor=actor,
                                summary=f"Status: {old} → {lead.get_status_display()}",
                                detail=note)
    return lead


def assign_lead(lead, staff, actor=None):
    lead.assigned_to = staff
    lead.last_activity_at = timezone.now()
    lead.save(update_fields=["assigned_to", "last_activity_at", "updated_at"])
    LeadActivity.objects.create(lead=lead, activity_type="assigned", actor=actor,
                                summary=f"Assigned to {staff.full_name if staff else 'nobody'}")
    if staff:
        notify_user(staff.user, f"Lead assigned: {lead.full_name}",
                    body=lead.phone, level="info", url=f"/dashboard/leads/{lead.pk}/")
    return lead


@transaction.atomic
def convert_lead(lead, actor=None, send_credentials=True):
    """SRS FR-LDM-06 — one-click conversion to a portal student."""
    User = get_user_model()
    existing = StudentProfile.objects.filter(lead=lead).first()
    if existing:
        return existing, None

    user = User.objects.filter(email__iexact=lead.email).first()
    password = None
    if user is None:
        base = (lead.email.split("@")[0] or "student")[:24]
        username = base
        i = 2
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1
        password = secrets.token_urlsafe(9)
        names = lead.full_name.split()
        user = User.objects.create_user(
            username=username, email=lead.email, password=password,
            first_name=names[0] if names else "", last_name=" ".join(names[1:]),
            role=Role.STUDENT, phone=lead.phone, email_verified=True)

    profile, _ = StudentProfile.objects.get_or_create(
        user=user,
        defaults={"lead": lead, "preferred_intake": lead.get_intended_intake_display() or "",
                  "preferred_level": lead.get_study_level_display() or "",
                  "english_test": lead.english_test, "english_score": lead.english_score,
                  "assigned_counsellor": lead.assigned_to})
    profile.lead = lead
    if lead.assigned_to and not profile.assigned_counsellor:
        profile.assigned_counsellor = lead.assigned_to
    profile.save()
    profile.preferred_destinations.set(lead.destinations.all())

    change_status(lead, LeadStatus.CONVERTED, actor=actor, note="Converted to student")
    LeadActivity.objects.create(lead=lead, activity_type="converted", actor=actor,
                                summary=f"Converted to student profile #{profile.pk}")

    if send_credentials and password:
        send_email(
            subject="Your Dream Spot Global student portal account",
            to=user.email,
            body=(f"Dear {lead.full_name},\n\nYour student portal is ready.\n\n"
                  f"Login: {user.email}\nTemporary password: {password}\n\n"
                  "Please sign in and change your password.\n\nDream Spot Global"))
    notify_user(user, "Welcome to your Dream Spot Global portal",
                body="Complete your profile and upload your documents to get started.",
                level="success", url="/portal/")
    return profile, password
