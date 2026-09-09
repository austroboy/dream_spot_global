"""Student portal (SRS section 7). Every queryset is scoped to request.user (FR-STU-14)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.forms import AcademicRecordForm, StudentProfileForm, UserDetailsForm
from apps.applications.models import DOCUMENT_TYPES, Application, Document
from apps.core.validators import validate_upload
from apps.institutions.models import Course, Shortlist
from apps.notifications.models import Message, MessageThread, Notification
from apps.notifications.services import notify_user


def _profile(request):
    profile = getattr(request.user, "student_profile", None)
    if profile is None:
        raise PermissionDenied("This area is for student accounts only.")
    return profile


@login_required
def home(request):
    profile = _profile(request)
    apps_qs = Application.objects.filter(student=profile) \
        .select_related("university", "course")
    docs = Document.objects.filter(student=profile)
    next_appt = profile.appointments.filter(start_datetime__gte=timezone.now(),
                                            status__in=["booked", "confirmed"]).first()
    thread = MessageThread.objects.filter(student=profile).first()
    recommended = Course.objects.filter(
        is_active=True,
        university__country__in=profile.preferred_destinations.all()
    ).select_related("university")[:4]
    return render(request, "portal/home.html", {
        "profile": profile,
        "applications": apps_qs,
        "primary_application": apps_qs.filter(is_active=True).first(),
        "documents": docs,
        "pending_docs": docs.filter(status__in=["pending", "reupload"]).count(),
        "next_appointment": next_appt,
        "unread": thread.unread_for(request.user) if thread else 0,
        "recommended": recommended,
        "notifications": Notification.objects.filter(recipient=request.user)[:5],
        "meta_title": "My dashboard",
    })


@login_required
def profile(request):
    profile = _profile(request)
    user_form = UserDetailsForm(request.POST or None, request.FILES or None,
                                instance=request.user)
    form = StudentProfileForm(request.POST or None, instance=profile)
    record_form = AcademicRecordForm()
    if request.method == "POST" and "save_profile" in request.POST:
        if user_form.is_valid() and form.is_valid():
            user_form.save()
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("portal:profile")
    return render(request, "portal/profile.html", {
        "profile": profile, "form": form, "user_form": user_form,
        "record_form": record_form,
        "records": profile.academic_records.all(),
        "meta_title": "My profile",
    })


@login_required
def add_academic_record(request):
    profile = _profile(request)
    form = AcademicRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.student = profile
        record.save()
        messages.success(request, "Academic record added.")
    return redirect("portal:profile")


@login_required
def delete_academic_record(request, pk):
    profile = _profile(request)
    record = get_object_or_404(profile.academic_records, pk=pk)
    record.delete()
    messages.success(request, "Academic record removed.")
    return redirect("portal:profile")


@login_required
def documents(request):
    profile = _profile(request)
    if request.method == "POST":
        f = request.FILES.get("file")
        doc_type = request.POST.get("document_type")
        if not f:
            messages.error(request, "Please choose a file to upload.")
        else:
            try:
                validate_upload(f)     # SRS FR-STU-06
                Document.objects.create(student=profile, document_type=doc_type,
                                        title=request.POST.get("title", ""), file=f)
                messages.success(request, "Document uploaded and queued for verification.")
            except Exception as exc:
                messages.error(request, str(exc))
        return redirect("portal:documents")
    docs = Document.objects.filter(student=profile)
    uploaded_types = set(docs.values_list("document_type", flat=True))
    checklist = [{"code": c, "label": l, "uploaded": c in uploaded_types}
                 for c, l in DOCUMENT_TYPES if c != "other"]
    return render(request, "portal/documents.html", {
        "documents": docs, "document_types": DOCUMENT_TYPES, "checklist": checklist,
        "meta_title": "My documents",
    })


@login_required
def document_download(request, pk):
    """SRS SEC-10 — documents are served through a permission-checked view only."""
    profile = _profile(request)
    doc = get_object_or_404(Document, pk=pk, student=profile)
    if not doc.file:
        raise Http404
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.filename)


@login_required
def document_delete(request, pk):
    profile = _profile(request)
    doc = get_object_or_404(Document, pk=pk, student=profile)
    if doc.status == "verified":
        messages.error(request, "Verified documents cannot be deleted.")
    else:
        doc.delete()
        messages.success(request, "Document removed.")
    return redirect("portal:documents")


@login_required
def applications(request):
    profile = _profile(request)
    return render(request, "portal/applications.html", {
        "applications": Application.objects.filter(student=profile)
                        .select_related("university", "course"),
        "meta_title": "My applications",
    })


@login_required
def application_detail(request, pk):
    profile = _profile(request)
    app = get_object_or_404(
        Application.objects.select_related("university", "course", "assigned_officer__user"),
        pk=pk, student=profile)
    return render(request, "portal/application_detail.html", {
        "application": app,
        "history": app.stage_history.select_related("actor")[:20],
        "documents": app.documents.all(),
        "meta_title": app.reference_no,
    })


@login_required
def appointments(request):
    profile = _profile(request)
    return render(request, "portal/appointments.html", {
        "upcoming": profile.appointments.filter(start_datetime__gte=timezone.now()),
        "past": profile.appointments.filter(start_datetime__lt=timezone.now()),
        "meta_title": "My appointments",
    })


@login_required
def shortlist(request):
    items = Shortlist.objects.filter(user=request.user) \
        .select_related("course", "course__university", "university")
    return render(request, "portal/shortlist.html",
                  {"items": items, "meta_title": "My shortlist"})


@login_required
def messages_view(request):
    profile = _profile(request)
    thread, _ = MessageThread.objects.get_or_create(student=profile)
    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            Message.objects.create(thread=thread, sender=request.user, body=body)
            if profile.assigned_counsellor:
                notify_user(profile.assigned_counsellor.user,
                            f"New message from {profile.full_name}", body=body[:120],
                            url=f"/dashboard/students/{profile.pk}/")
            messages.success(request, "Message sent.")
        return redirect("portal:messages")
    thread.messages.exclude(sender=request.user).update(is_read=True)
    return render(request, "portal/messages.html", {
        "thread": thread, "items": thread.messages.select_related("sender"),
        "meta_title": "Messages",
    })


@login_required
def notifications(request):
    items = Notification.objects.filter(recipient=request.user)
    if request.method == "POST":
        items.update(is_read=True)
        return redirect("portal:notifications")
    return render(request, "portal/notifications.html",
                  {"items": items[:50], "meta_title": "Notifications"})


@login_required
def export_data(request):
    """SRS FR-STU-13 / PRV-04 — student data export."""
    import json

    from django.http import HttpResponse
    profile = _profile(request)
    payload = {
        "account": {"name": profile.full_name, "email": request.user.email,
                    "phone": request.user.phone},
        "profile": {f.name: str(getattr(profile, f.name))
                    for f in profile._meta.fields if f.name not in ("id", "user", "lead")},
        "applications": [{"reference": a.reference_no, "university": a.university.name,
                          "course": a.course.title, "stage": a.get_stage_display()}
                         for a in profile.applications.all()],
        "documents": [{"type": d.get_document_type_display(), "status": d.status}
                      for d in profile.documents.all()],
    }
    resp = HttpResponse(json.dumps(payload, indent=2), content_type="application/json")
    resp["Content-Disposition"] = 'attachment; filename="my-dreamspot-data.json"'
    return resp
