"""Staff dashboard (SRS section 8). RBAC enforced on every view (SRS 12.2)."""
import csv
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Role, StaffProfile, StudentProfile, User
from apps.accounts.permissions import require_capability, user_can
from apps.applications.models import (DOCUMENT_TYPES, Application, ApplicationStageHistory,
                                      Document, Stage)
from apps.appointments.models import Appointment, Availability, BlackoutDate
from apps.core.models import AuditLog, ContactMessage, SiteSettings
from apps.dashboard.forms import (CONTENT_MODELS, ApplicationForm, AvailabilityForm,
                                  BlackoutForm, LeadForm, LeadNoteForm, SiteSettingsForm,
                                  StaffProfileForm, StaffUserForm, StageChangeForm,
                                  build_form)
from apps.destinations.models import Country
from apps.events.models import Event, EventRegistration
from apps.leads.models import Lead, LeadActivity, LeadNote, LeadStatus, NewsletterSubscriber
from apps.leads.services import assign_lead, change_status, convert_lead
from apps.notifications.models import Message, MessageThread
from apps.notifications.services import notify_user, send_email

PAGE_SIZE = 20


def staff_only(view):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_staff_member:
            raise PermissionDenied("Staff access only.")
        return view(request, *args, **kwargs)
    _wrapped.__name__ = view.__name__
    return _wrapped


def _date_range(request):
    preset = request.GET.get("range", "30")
    today = timezone.localdate()
    if preset == "today":
        start = today
    elif preset == "custom" and request.GET.get("from"):
        from django.utils.dateparse import parse_date
        start = parse_date(request.GET["from"]) or today - timedelta(days=30)
    else:
        try:
            start = today - timedelta(days=int(preset))
        except ValueError:
            start = today - timedelta(days=30)
    end = today
    if request.GET.get("to"):
        from django.utils.dateparse import parse_date
        end = parse_date(request.GET["to"]) or today
    return start, end, preset


def _visible_leads(user):
    """SRS 12.2 — counsellors see only their own leads."""
    qs = Lead.objects.select_related("assigned_to__user").prefetch_related("destinations")
    if user_can(user, "view_all_leads"):
        return qs
    if user.is_counsellor:
        return qs.filter(assigned_to__user=user)
    return qs.none()


def _visible_students(user):
    qs = StudentProfile.objects.select_related("user", "assigned_counsellor__user")
    if user.is_admin_role:
        return qs
    if user.is_counsellor:
        return qs.filter(assigned_counsellor__user=user)
    if user.is_officer:
        return qs.filter(applications__assigned_officer__user=user).distinct()
    return qs.none()


def _visible_applications(user):
    qs = Application.objects.select_related("student__user", "university", "course",
                                            "assigned_officer__user")
    if user.is_admin_role:
        return qs
    if user.is_officer:
        return qs.filter(assigned_officer__user=user)
    if user.is_counsellor:
        return qs.filter(student__assigned_counsellor__user=user)
    return qs.none()


# ---------------------------------------------------------------- overview
@staff_only
def home(request):
    start, end, preset = _date_range(request)
    leads = _visible_leads(request.user)
    period = leads.filter(created_at__date__gte=start, created_at__date__lte=end)
    prev_start = start - (end - start) - timedelta(days=1)
    previous = leads.filter(created_at__date__gte=prev_start, created_at__date__lt=start)

    apps_qs = _visible_applications(request.user)
    today = timezone.localdate()

    def delta(now_count, before_count):
        if not before_count:
            return 100 if now_count else 0
        return round((now_count - before_count) / before_count * 100)

    converted = period.filter(status=LeadStatus.CONVERTED).count()
    kpis = [
        {"label": "Leads in period", "value": period.count(), "icon": "inbox",
         "delta": delta(period.count(), previous.count())},
        {"label": "New today", "value": leads.filter(created_at__date=today).count(),
         "icon": "zap", "delta": None},
        {"label": "Active students", "value": _visible_students(request.user).count(),
         "icon": "users", "delta": None},
        {"label": "Applications in progress", "icon": "file-text", "delta": None,
         "value": apps_qs.filter(is_active=True).exclude(stage=Stage.DEPARTED).count()},
        {"label": "Offers received", "icon": "mail-check", "delta": None,
         "value": apps_qs.filter(stage__in=[Stage.OFFER_RECEIVED, Stage.OFFER_ACCEPTED,
                                            Stage.DEPOSIT_PAID, Stage.CAS_ISSUED]).count()},
        {"label": "Visas granted", "icon": "plane", "delta": None,
         "value": apps_qs.filter(visa_status="granted").count()},
        {"label": "Appointments today", "icon": "calendar", "delta": None,
         "value": Appointment.objects.filter(start_datetime__date=today)
                  .exclude(status="cancelled").count()},
        {"label": "Conversion rate", "icon": "trending-up", "delta": None,
         "value": f"{round(converted / period.count() * 100) if period.count() else 0}%"},
    ]

    attention = {
        "overdue_leads": [l for l in leads.filter(status__in=["new", "contacted",
                                                              "qualified", "scheduled"])[:200]
                          if l.is_overdue][:8],
        "pending_documents": Document.objects.filter(status__in=["pending", "reupload"])
                             .select_related("student__user")[:8],
        "deadlines": apps_qs.filter(deadline__isnull=False,
                                    deadline__lte=today + timedelta(days=14),
                                    deadline__gte=today)[:8],
    }

    return render(request, "dashboard/home.html", {
        "kpis": kpis, "preset": preset, "start": start, "end": end,
        "attention": attention,
        "recent_leads": leads[:8],
        "activity": LeadActivity.objects.select_related("lead", "actor")[:10],
        "meta_title": "Dashboard",
    })


@staff_only
def chart_data(request):
    """JSON feed for Chart.js widgets (SRS FR-DSH-02)."""
    start, end, _ = _date_range(request)
    leads = _visible_leads(request.user).filter(created_at__date__gte=start,
                                                created_at__date__lte=end)
    by_day = list(leads.annotate(d=TruncDate("created_at")).values("d")
                  .annotate(n=Count("id")).order_by("d"))
    by_source = list(leads.values("source").annotate(n=Count("id")).order_by("-n"))
    by_country = list(leads.values("destinations__name").annotate(n=Count("id"))
                      .exclude(destinations__name=None).order_by("-n")[:8])
    apps_qs = _visible_applications(request.user)
    funnel = [{"stage": label, "n": apps_qs.filter(stage=value).count()}
              for value, label in Stage.choices]
    counsellors = list(
        StaffProfile.objects.filter(user__role=Role.COUNSELLOR)
        .annotate(total=Count("leads"),
                  won=Count("leads", filter=Q(leads__status=LeadStatus.CONVERTED)))
        .values("user__first_name", "user__last_name", "total", "won"))
    monthly = list(leads.annotate(m=TruncMonth("created_at")).values("m")
                   .annotate(n=Count("id")).order_by("m"))
    return JsonResponse({
        "by_day": [{"label": r["d"].strftime("%d %b"), "value": r["n"]} for r in by_day],
        "by_source": [{"label": dict(Lead._meta.get_field("source").choices).get(
            r["source"], r["source"]), "value": r["n"]} for r in by_source],
        "by_country": [{"label": r["destinations__name"], "value": r["n"]}
                       for r in by_country],
        "funnel": [{"label": f["stage"], "value": f["n"]} for f in funnel],
        "counsellors": [{"label": f"{c['user__first_name']} {c['user__last_name']}".strip(),
                         "value": c["total"], "won": c["won"]} for c in counsellors],
        "monthly": [{"label": r["m"].strftime("%b %Y"), "value": r["n"]} for r in monthly],
    })


# ---------------------------------------------------------------- leads
@staff_only
@require_capability("view_own_leads")
def lead_list(request):
    qs = _visible_leads(request.user)
    g = request.GET
    if g.get("status"):
        qs = qs.filter(status=g["status"])
    if g.get("source"):
        qs = qs.filter(source=g["source"])
    if g.get("country"):
        qs = qs.filter(destinations__slug=g["country"])
    if g.get("counsellor") and user_can(request.user, "view_all_leads"):
        qs = qs.filter(assigned_to_id=g["counsellor"])
    if g.get("q"):
        term = g["q"]
        qs = qs.filter(Q(full_name__icontains=term) | Q(email__icontains=term)
                       | Q(phone__icontains=term))
    if g.get("from"):
        qs = qs.filter(created_at__date__gte=g["from"])
    if g.get("to"):
        qs = qs.filter(created_at__date__lte=g["to"])
    sort = g.get("sort", "-created_at")
    allowed_sorts = {"created_at", "-created_at", "full_name", "-full_name",
                     "status", "-status", "last_activity_at", "-last_activity_at"}
    qs = qs.order_by(sort if sort in allowed_sorts else "-created_at").distinct()

    if g.get("export") == "csv":
        return _export_leads(qs)

    page = Paginator(qs, PAGE_SIZE).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    return render(request, "dashboard/leads/list.html", {
        "page_obj": page,
        "statuses": LeadStatus.choices,
        "sources": Lead._meta.get_field("source").choices,
        "countries": Country.objects.filter(is_active=True),
        "counsellors": StaffProfile.objects.filter(user__role=Role.COUNSELLOR),
        "selected": g, "querystring": params.urlencode(),
        "can_reassign": user_can(request.user, "reassign_leads"),
        "meta_title": "Leads",
    })


def _export_leads(qs):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="leads.csv"'
    writer = csv.writer(resp)
    writer.writerow(["Name", "Email", "Phone", "Destinations", "Level", "Intake",
                     "Source", "Status", "Assigned to", "Created"])
    for lead in qs[:5000]:
        writer.writerow([lead.full_name, lead.email, lead.phone, lead.destination_names,
                         lead.get_study_level_display(), lead.get_intended_intake_display(),
                         lead.get_source_display(), lead.get_status_display(),
                         lead.assigned_to.full_name if lead.assigned_to else "",
                         lead.created_at.strftime("%Y-%m-%d %H:%M")])
    return resp


@staff_only
@require_capability("view_own_leads")
def lead_kanban(request):
    """SRS FR-LDM-08."""
    qs = _visible_leads(request.user)
    columns = [{"status": value, "label": label,
                "items": list(qs.filter(status=value)[:50]),
                "count": qs.filter(status=value).count()}
               for value, label in LeadStatus.choices]
    return render(request, "dashboard/leads/kanban.html",
                  {"columns": columns, "meta_title": "Lead pipeline"})


@staff_only
@require_capability("view_own_leads")
def lead_detail(request, pk):
    lead = get_object_or_404(_visible_leads(request.user), pk=pk)
    note_form = LeadNoteForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "note" and note_form.is_valid():
            note = note_form.save(commit=False)
            note.lead = lead
            note.author = request.user
            note.save()
            LeadActivity.objects.create(lead=lead, activity_type="note", actor=request.user,
                                        summary="Note added")
            lead.touch()
            messages.success(request, "Note added.")
        elif action == "status":
            change_status(lead, request.POST.get("status"), actor=request.user,
                          note=request.POST.get("note", ""))
            messages.success(request, "Lead status updated.")
        elif action == "assign":
            if not user_can(request.user, "reassign_leads"):
                raise PermissionDenied("Only administrators can reassign leads.")
            staff = StaffProfile.objects.filter(pk=request.POST.get("assigned_to")).first()
            assign_lead(lead, staff, actor=request.user)
            messages.success(request, "Lead reassigned.")
        elif action == "log":
            LeadActivity.objects.create(
                lead=lead, activity_type=request.POST.get("activity_type", "call"),
                actor=request.user, summary=request.POST.get("summary", "Interaction logged"),
                detail=request.POST.get("detail", ""))
            lead.touch()
            messages.success(request, "Interaction logged.")
        elif action == "follow_up":
            from django.utils.dateparse import parse_datetime
            when = parse_datetime(request.POST.get("next_follow_up", ""))
            if when:
                lead.next_follow_up = timezone.make_aware(when) if timezone.is_naive(when) \
                    else when
                lead.save(update_fields=["next_follow_up"])
                messages.success(request, "Follow-up reminder set.")
        elif action == "convert":
            if not user_can(request.user, "convert_lead"):
                raise PermissionDenied()
            profile, password = convert_lead(lead, actor=request.user)
            messages.success(request, f"Converted. Student profile #{profile.pk} created"
                                      + (" and portal credentials emailed." if password
                                         else "."))
            return redirect("dashboard:student_detail", pk=profile.pk)
        elif action == "delete":
            if not request.user.is_admin_role:
                raise PermissionDenied()
            lead.soft_delete()
            messages.success(request, "Lead deleted.")
            return redirect("dashboard:lead_list")
        return redirect("dashboard:lead_detail", pk=pk)

    return render(request, "dashboard/leads/detail.html", {
        "lead": lead, "note_form": note_form,
        "activities": lead.activities.select_related("actor")[:50],
        "notes": lead.notes.select_related("author")[:50],
        "statuses": LeadStatus.choices,
        "counsellors": StaffProfile.objects.filter(user__role=Role.COUNSELLOR),
        "can_reassign": user_can(request.user, "reassign_leads"),
        "can_convert": user_can(request.user, "convert_lead"),
        "appointments": lead.appointments.all(),
        "meta_title": lead.full_name,
    })


@staff_only
@require_capability("edit_lead")
def lead_bulk(request):
    """SRS FR-LDM-07."""
    if request.method != "POST":
        return redirect("dashboard:lead_list")
    ids = request.POST.getlist("selected")
    qs = _visible_leads(request.user).filter(pk__in=ids)
    action = request.POST.get("bulk_action")
    count = qs.count()
    if action == "status" and request.POST.get("bulk_status"):
        for lead in qs:
            change_status(lead, request.POST["bulk_status"], actor=request.user)
        messages.success(request, f"Updated {count} leads.")
    elif action == "assign":
        if not user_can(request.user, "reassign_leads"):
            raise PermissionDenied()
        staff = StaffProfile.objects.filter(pk=request.POST.get("bulk_assignee")).first()
        for lead in qs:
            assign_lead(lead, staff, actor=request.user)
        messages.success(request, f"Assigned {count} leads.")
    elif action == "export":
        return _export_leads(qs)
    elif action == "delete":
        if not request.user.is_admin_role:
            raise PermissionDenied()
        for lead in qs:
            lead.soft_delete()
        messages.success(request, f"Deleted {count} leads.")
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/leads/"))


@staff_only
@require_capability("edit_lead")
def lead_move(request, pk):
    """Kanban drag-and-drop endpoint."""
    lead = get_object_or_404(_visible_leads(request.user), pk=pk)
    status = request.POST.get("status")
    if status in dict(LeadStatus.choices):
        change_status(lead, status, actor=request.user, note="Moved on the pipeline board")
        return JsonResponse({"ok": True, "status": lead.get_status_display()})
    return JsonResponse({"ok": False}, status=400)


# ---------------------------------------------------------------- students
@staff_only
@require_capability("view_students")
def student_list(request):
    qs = _visible_students(request.user).annotate(app_count=Count("applications"))
    if request.GET.get("q"):
        term = request.GET["q"]
        qs = qs.filter(Q(user__first_name__icontains=term) | Q(user__last_name__icontains=term)
                       | Q(user__email__icontains=term))
    page = Paginator(qs.order_by("-created_at"), PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "dashboard/students/list.html",
                  {"page_obj": page, "selected": request.GET, "meta_title": "Students"})


@staff_only
@require_capability("view_students")
def student_detail(request, pk):
    student = get_object_or_404(_visible_students(request.user), pk=pk)
    thread, _ = MessageThread.objects.get_or_create(student=student)
    if request.method == "POST" and request.POST.get("action") == "message":
        body = (request.POST.get("body") or "").strip()
        if body:
            Message.objects.create(thread=thread, sender=request.user, body=body)
            notify_user(student.user, "New message from your counsellor",
                        body=body[:120], url="/portal/messages/")
            messages.success(request, "Message sent to the student.")
        return redirect("dashboard:student_detail", pk=pk)
    return render(request, "dashboard/students/detail.html", {
        "student": student,
        "applications": student.applications.select_related("university", "course"),
        "documents": student.documents.all(),
        "appointments": student.appointments.all(),
        "thread": thread, "thread_messages": thread.messages.select_related("sender"),
        "can_verify": user_can(request.user, "verify_documents"),
        "meta_title": student.full_name,
    })


# ---------------------------------------------------------------- applications
@staff_only
@require_capability("edit_applications")
def application_list(request):
    qs = _visible_applications(request.user)
    g = request.GET
    if g.get("stage"):
        qs = qs.filter(stage=g["stage"])
    if g.get("visa"):
        qs = qs.filter(visa_status=g["visa"])
    if g.get("country"):
        qs = qs.filter(university__country__slug=g["country"])
    if g.get("q"):
        qs = qs.filter(Q(reference_no__icontains=g["q"])
                       | Q(student__user__first_name__icontains=g["q"])
                       | Q(student__user__last_name__icontains=g["q"]))
    if g.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="applications.csv"'
        w = csv.writer(resp)
        w.writerow(["Reference", "Student", "University", "Course", "Intake", "Stage",
                    "Visa status", "Officer", "Deadline"])
        for a in qs[:5000]:
            w.writerow([a.reference_no, a.student.full_name, a.university.name,
                        a.course.title, a.intake, a.get_stage_display(),
                        a.get_visa_status_display(),
                        a.assigned_officer.full_name if a.assigned_officer else "",
                        a.deadline or ""])
        return resp
    page = Paginator(qs.order_by("-created_at"), PAGE_SIZE).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    return render(request, "dashboard/applications/list.html", {
        "page_obj": page, "stages": Stage.choices,
        "visa_statuses": Application.STATUS_VISA,
        "countries": Country.objects.filter(is_active=True),
        "selected": g, "querystring": params.urlencode(),
        "meta_title": "Applications",
    })


@staff_only
@require_capability("edit_applications")
def application_create(request):
    form = ApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        app = form.save()
        ApplicationStageHistory.objects.create(application=app, from_stage="",
                                               to_stage=app.stage, actor=request.user,
                                               note="Application created")
        messages.success(request, f"Application {app.reference_no} created.")
        return redirect("dashboard:application_detail", pk=app.pk)
    return render(request, "dashboard/applications/form.html",
                  {"form": form, "meta_title": "New application"})


@staff_only
@require_capability("edit_applications")
def application_detail(request, pk):
    app = get_object_or_404(_visible_applications(request.user), pk=pk)
    form = ApplicationForm(request.POST or None, instance=app)
    stage_form = StageChangeForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "stage":
            stage_form = StageChangeForm(request.POST)
            if stage_form.is_valid():
                old = app.stage
                app.stage = stage_form.cleaned_data["stage"]
                app.save(update_fields=["stage", "updated_at"])
                ApplicationStageHistory.objects.create(
                    application=app, from_stage=old, to_stage=app.stage,
                    note=stage_form.cleaned_data["note"], actor=request.user)
                if stage_form.cleaned_data["notify_student"]:
                    notify_user(app.student.user,
                                f"Application {app.reference_no} update",
                                body=f"New stage: {app.get_stage_display()}",
                                level="success",
                                url=f"/portal/applications/{app.pk}/")
                    send_email(
                        subject=f"Update on your application {app.reference_no}",
                        to=app.student.user.email,
                        body=(f"Dear {app.student.full_name},\n\nYour application for "
                              f"{app.course.title} at {app.university.name} has moved to: "
                              f"{app.get_stage_display()}.\n\n{stage_form.cleaned_data['note']}"
                              "\n\nDream Spot Global"))
                messages.success(request, "Stage updated and student notified.")
        elif action == "save" and form.is_valid():
            form.save()
            messages.success(request, "Application updated.")
        return redirect("dashboard:application_detail", pk=pk)
    return render(request, "dashboard/applications/detail.html", {
        "application": app, "form": form, "stage_form": stage_form,
        "history": app.stage_history.select_related("actor"),
        "documents": app.student.documents.all(),
        "can_verify": user_can(request.user, "verify_documents"),
        "meta_title": app.reference_no,
    })


# ---------------------------------------------------------------- documents
@staff_only
@require_capability("verify_documents")
def document_queue(request):
    qs = Document.objects.select_related("student__user").order_by("-created_at")
    status = request.GET.get("status", "pending")
    if status != "all":
        qs = qs.filter(status=status)
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "dashboard/documents/queue.html", {
        "page_obj": page, "status": status, "types": DOCUMENT_TYPES,
        "meta_title": "Document verification",
    })


@staff_only
@require_capability("verify_documents")
def document_review(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        decision = request.POST.get("decision")
        if decision in {"verified", "rejected", "reupload"}:
            doc.status = decision
            doc.remarks = request.POST.get("remarks", "")
            doc.reviewed_by = request.user
            doc.reviewed_at = timezone.now()
            doc.save()
            level = {"verified": "success", "rejected": "danger",
                     "reupload": "warning"}[decision]
            notify_user(doc.student.user,
                        f"{doc.get_document_type_display()}: {doc.get_status_display()}",
                        body=doc.remarks, level=level, url="/portal/documents/")
            send_email(
                subject=f"Document {doc.get_status_display().lower()} — Dream Spot Global",
                to=doc.student.user.email,
                body=(f"Dear {doc.student.full_name},\n\nYour "
                      f"{doc.get_document_type_display()} has been reviewed: "
                      f"{doc.get_status_display()}.\n{doc.remarks}\n\nDream Spot Global"))
            messages.success(request, "Document reviewed and the student notified.")
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/documents/"))


@staff_only
@require_capability("view_students")
def document_download(request, pk):
    """SRS SEC-10 / PRV-07 — access is permission-checked and audited."""
    doc = get_object_or_404(Document, pk=pk)
    if not user_can(request.user, "view_students"):
        raise PermissionDenied()
    if request.user.is_counsellor and doc.student.assigned_counsellor and \
            doc.student.assigned_counsellor.user_id != request.user.id:
        raise PermissionDenied("This student is assigned to another counsellor.")
    AuditLog.objects.create(actor=request.user, action="view", model_name="Document",
                            object_id=str(doc.pk), object_repr=str(doc))
    if not doc.file:
        raise Http404
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.filename)


# ---------------------------------------------------------------- appointments
@staff_only
@require_capability("manage_appointments")
def appointment_list(request):
    qs = Appointment.objects.select_related("counsellor__user", "destination")
    if request.user.is_counsellor:
        qs = qs.filter(counsellor__user=request.user)
    tab = request.GET.get("tab", "upcoming")
    if tab == "past":
        qs = qs.filter(start_datetime__lt=timezone.now()).order_by("-start_datetime")
    else:
        qs = qs.filter(start_datetime__gte=timezone.now()).order_by("start_datetime")
    if request.method == "POST":
        appt = get_object_or_404(Appointment, pk=request.POST.get("appointment"))
        appt.status = request.POST.get("status", appt.status)
        appt.save(update_fields=["status", "updated_at"])
        messages.success(request, "Appointment updated.")
        return redirect("dashboard:appointment_list")
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "dashboard/appointments/list.html", {
        "page_obj": page, "tab": tab, "statuses": Appointment.STATUS,
        "meta_title": "Appointments",
    })


@staff_only
@require_capability("manage_appointments")
def availability_view(request):
    form = AvailabilityForm(request.POST or None)
    blackout_form = BlackoutForm()
    if request.method == "POST":
        if request.POST.get("action") == "blackout":
            blackout_form = BlackoutForm(request.POST)
            if blackout_form.is_valid():
                blackout_form.save()
                messages.success(request, "Blackout date added.")
                return redirect("dashboard:availability")
        elif form.is_valid():
            form.save()
            messages.success(request, "Availability rule saved.")
            return redirect("dashboard:availability")
    return render(request, "dashboard/appointments/availability.html", {
        "form": form, "blackout_form": blackout_form,
        "rules": Availability.objects.select_related("counsellor__user"),
        "blackouts": BlackoutDate.objects.select_related("counsellor__user"),
        "meta_title": "Counsellor availability",
    })


@staff_only
@require_capability("manage_appointments")
def availability_delete(request, pk):
    get_object_or_404(Availability, pk=pk).delete()
    messages.success(request, "Availability rule removed.")
    return redirect("dashboard:availability")


# ---------------------------------------------------------------- content CRUD
def _content_config(key):
    cfg = CONTENT_MODELS.get(key)
    if not cfg:
        raise Http404("Unknown content type")
    return cfg


@staff_only
def content_list(request, key):
    cfg = _content_config(key)
    if not user_can(request.user, cfg["capability"]):
        raise PermissionDenied()
    Model = cfg["model"]
    qs = Model.objects.all()
    if not qs.ordered:
        qs = qs.order_by("-pk")
    q = request.GET.get("q")
    if q and cfg["search"]:
        cond = Q()
        for field in cfg["search"]:
            cond |= Q(**{f"{field}__icontains": q})
        qs = qs.filter(cond)
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    rows = []
    for obj in page.object_list:
        cells = []
        for col in cfg["columns"]:
            getter = getattr(obj, f"get_{col}_display", None)
            value = getter() if getter else getattr(obj, col, "")
            cells.append(value)
        rows.append({"obj": obj, "cells": cells})
    return render(request, "dashboard/content/list.html", {
        "cfg": cfg, "key": key, "page_obj": page, "rows": rows, "q": q or "",
        "columns": [c.replace("_", " ").title() for c in cfg["columns"]],
        "meta_title": cfg["label"],
    })


@staff_only
def content_edit(request, key, pk=None):
    cfg = _content_config(key)
    if not user_can(request.user, cfg["capability"]):
        raise PermissionDenied()
    Model = cfg["model"]
    instance = get_object_or_404(Model, pk=pk) if pk else None
    FormClass = build_form(Model, widgets=cfg.get("widgets"))
    form = FormClass(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{cfg['label'][:-1] if cfg['label'].endswith('s') else cfg['label']} saved.")
        if request.POST.get("save_and_continue"):
            return redirect("dashboard:content_edit", key=key, pk=obj.pk)
        return redirect("dashboard:content_list", key=key)
    return render(request, "dashboard/content/form.html", {
        "cfg": cfg, "key": key, "form": form, "instance": instance,
        "meta_title": f"{'Edit' if instance else 'New'} — {cfg['label']}",
    })


@staff_only
def content_delete(request, key, pk):
    cfg = _content_config(key)
    if not user_can(request.user, cfg["capability"]):
        raise PermissionDenied()
    obj = get_object_or_404(cfg["model"], pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Deleted.")
        return redirect("dashboard:content_list", key=key)
    return render(request, "dashboard/content/confirm_delete.html",
                  {"cfg": cfg, "key": key, "object": obj, "meta_title": "Confirm delete"})


# ---------------------------------------------------------------- enquiries etc.
@staff_only
def enquiry_list(request):
    qs = ContactMessage.objects.all()
    if request.method == "POST":
        ContactMessage.objects.filter(pk=request.POST.get("pk")).update(is_read=True)
        return redirect("dashboard:enquiries")
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "dashboard/enquiries.html",
                  {"page_obj": page, "meta_title": "Contact messages"})


@staff_only
def event_registrations(request, pk):
    event = get_object_or_404(Event, pk=pk)
    regs = event.registrations.select_related("destination_interest")
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{event.slug}-registrations.csv"'
        w = csv.writer(resp)
        w.writerow(["Name", "Email", "Phone", "Destination", "Level", "Status", "Attended"])
        for r in regs:
            w.writerow([r.full_name, r.email, r.phone,
                        r.destination_interest.name if r.destination_interest else "",
                        r.study_level, r.get_status_display(), "Yes" if r.attended else "No"])
        return resp
    if request.method == "POST":
        reg = get_object_or_404(EventRegistration, pk=request.POST.get("registration"))
        reg.attended = not reg.attended
        reg.status = "attended" if reg.attended else "confirmed"
        reg.save(update_fields=["attended", "status", "updated_at"])
        return redirect("dashboard:event_registrations", pk=pk)
    return render(request, "dashboard/events/registrations.html", {
        "event": event, "registrations": regs, "meta_title": "Registrations"})


@staff_only
@require_capability("site_settings")
def newsletter_list(request):
    qs = NewsletterSubscriber.objects.all()
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        w = csv.writer(resp)
        w.writerow(["Email", "Confirmed", "Unsubscribed", "Joined"])
        for s in qs:
            w.writerow([s.email, s.is_confirmed, s.unsubscribed,
                        s.created_at.strftime("%Y-%m-%d")])
        return resp
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "dashboard/newsletter.html",
                  {"page_obj": page, "meta_title": "Newsletter subscribers"})


# ---------------------------------------------------------------- users & settings
@staff_only
@require_capability("manage_users")
def user_list(request):
    qs = User.objects.exclude(role=Role.STUDENT).select_related("staff_profile")
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "dashboard/users/list.html", {
        "page_obj": page, "roles": Role.choices, "meta_title": "Staff users"})


@staff_only
@require_capability("manage_users")
def user_edit(request, pk=None):
    import secrets
    instance = get_object_or_404(User, pk=pk) if pk else None
    form = StaffUserForm(request.POST or None, instance=instance)
    profile = getattr(instance, "staff_profile", None) if instance else None
    profile_form = StaffProfileForm(request.POST or None, request.FILES or None,
                                    instance=profile)
    if request.method == "POST" and form.is_valid() and profile_form.is_valid():
        user = form.save(commit=False)
        password = None
        if instance is None:
            base = user.email.split("@")[0][:24]
            username = base
            i = 2
            while User.objects.filter(username=username).exists():
                username = f"{base}{i}"
                i += 1
            user.username = username
            password = secrets.token_urlsafe(9)
            user.set_password(password)
        user.is_staff = user.role in {Role.ADMIN}
        user.save()
        sp = profile_form.save(commit=False)
        sp.user = user
        sp.save()
        profile_form.save_m2m()
        if password:
            send_email(subject="Your Dream Spot Global staff account", to=user.email,
                       body=(f"Hello {user.first_name},\n\nAn account has been created "
                             f"for you.\nLogin: {user.email}\nTemporary password: {password}\n\n"
                             "Please sign in and change your password immediately."))
        messages.success(request, "Staff user saved."
                         + (" Credentials emailed." if password else ""))
        return redirect("dashboard:user_list")
    return render(request, "dashboard/users/form.html", {
        "form": form, "profile_form": profile_form, "instance": instance,
        "meta_title": "Staff user"})


@staff_only
@require_capability("manage_users")
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, "User status updated.")
    return redirect("dashboard:user_list")


@staff_only
@require_capability("manage_users")
def roles_view(request):
    from apps.accounts.permissions import CAPABILITIES
    matrix = []
    for cap, roles in CAPABILITIES.items():
        matrix.append({"capability": cap.replace("_", " ").title(),
                       "roles": {r[0]: (r[0] in roles or r[0] == Role.ADMIN)
                                 for r in Role.choices}})
    return render(request, "dashboard/users/roles.html", {
        "matrix": matrix, "roles": Role.choices, "meta_title": "Roles & permissions"})


@staff_only
@require_capability("site_settings")
def settings_view(request):
    obj = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Site settings saved.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html",
                  {"form": form, "meta_title": "Site settings"})


@staff_only
@require_capability("view_audit_log")
def audit_log(request):
    qs = AuditLog.objects.select_related("actor")
    if request.GET.get("model"):
        qs = qs.filter(model_name=request.GET["model"])
    if request.GET.get("action"):
        qs = qs.filter(action=request.GET["action"])
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    models = AuditLog.objects.values_list("model_name", flat=True).distinct()
    return render(request, "dashboard/audit.html", {
        "page_obj": page, "models": models, "actions": AuditLog.ACTIONS,
        "selected": request.GET, "meta_title": "Audit log"})


# ---------------------------------------------------------------- reports
@staff_only
@require_capability("view_reports")
def reports(request):
    start, end, preset = _date_range(request)
    leads = _visible_leads(request.user).filter(created_at__date__gte=start,
                                                created_at__date__lte=end)
    apps_qs = _visible_applications(request.user)
    total = leads.count()
    converted = leads.filter(status=LeadStatus.CONVERTED).count()

    by_source = leads.values("source").annotate(
        n=Count("id"), won=Count("id", filter=Q(status=LeadStatus.CONVERTED))).order_by("-n")
    source_rows = [{
        "label": dict(Lead._meta.get_field("source").choices).get(r["source"], r["source"]),
        "count": r["n"], "won": r["won"],
        "rate": round(r["won"] / r["n"] * 100) if r["n"] else 0} for r in by_source]

    counsellor_rows = [{
        "label": s.full_name, "count": s.leads.count(),
        "won": s.leads.filter(status=LeadStatus.CONVERTED).count(),
        "rate": round(s.leads.filter(status=LeadStatus.CONVERTED).count()
                      / s.leads.count() * 100) if s.leads.count() else 0}
        for s in StaffProfile.objects.filter(user__role=Role.COUNSELLOR)]

    destination_rows = [{
        "label": c.name, "count": apps_qs.filter(university__country=c).count(),
        "won": apps_qs.filter(university__country=c, visa_status="granted").count()}
        for c in Country.objects.filter(is_active=True)]

    visa_total = apps_qs.filter(visa_status__in=["granted", "refused"]).count()
    visa_granted = apps_qs.filter(visa_status="granted").count()

    report = {
        "total_leads": total, "converted": converted,
        "conversion_rate": round(converted / total * 100) if total else 0,
        "source_rows": source_rows, "counsellor_rows": counsellor_rows,
        "destination_rows": destination_rows,
        "visa_rate": round(visa_granted / visa_total * 100) if visa_total else 0,
        "visa_total": visa_total, "visa_granted": visa_granted,
        "intake_rows": [{"label": v or "Unspecified",
                         "count": apps_qs.filter(intake=v).count()}
                        for v in apps_qs.values_list("intake", flat=True).distinct()[:12]],
    }

    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="report.csv"'
        w = csv.writer(resp)
        w.writerow(["Section", "Label", "Count", "Converted", "Rate %"])
        for r in source_rows:
            w.writerow(["Source", r["label"], r["count"], r["won"], r["rate"]])
        for r in counsellor_rows:
            w.writerow(["Counsellor", r["label"], r["count"], r["won"], r["rate"]])
        for r in destination_rows:
            w.writerow(["Destination", r["label"], r["count"], r["won"], ""])
        return resp

    return render(request, "dashboard/reports.html", {
        "report": report, "start": start, "end": end, "preset": preset,
        "meta_title": "Reports"})
