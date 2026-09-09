"""Dashboard forms (SRS section 8)."""
from django import forms

from apps.accounts.forms import StyledModelForm
from apps.accounts.models import Role, StaffProfile, User
from apps.applications.models import Application, Document
from apps.appointments.models import Availability, BlackoutDate
from apps.blog.models import BlogPost, Category, Tag
from apps.core.models import (HeroSlide, HomepageSection, JourneyStep, Page, SiteSettings,
                              TeamMember, WhyUsPoint)
from apps.destinations.models import CostOfLiving, Country, Intake, VisaRequirement
from apps.events.models import Event
from apps.faqs.models import FAQ, FAQCategory
from apps.institutions.models import Course, University
from apps.leads.models import Lead, LeadNote
from apps.notifications.models import EmailTemplate
from apps.scholarships.models import Scholarship
from apps.services.models import Service, ServiceStep
from apps.testimonials.models import Testimonial


class LeadForm(StyledModelForm):
    class Meta:
        model = Lead
        fields = ["full_name", "email", "phone", "destinations", "study_level",
                  "intended_intake", "last_qualification", "gpa", "english_test",
                  "english_score", "message", "source", "status", "priority",
                  "assigned_to", "next_follow_up", "lost_reason"]
        widgets = {"destinations": forms.CheckboxSelectMultiple,
                   "next_follow_up": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class LeadNoteForm(StyledModelForm):
    class Meta:
        model = LeadNote
        fields = ["body", "attachment"]
        labels = {"body": "Add a note"}


class ApplicationForm(StyledModelForm):
    class Meta:
        model = Application
        fields = ["student", "university", "course", "intake", "study_level", "stage",
                  "sub_status", "priority", "assigned_officer", "application_fee",
                  "tuition_deposit", "currency", "offer_type", "submitted_on",
                  "offer_received_on", "deadline", "visa_status", "visa_applied_on",
                  "biometrics_on", "interview_on", "visa_decision_on",
                  "visa_refusal_reason", "internal_notes", "is_active"]
        widgets = {f: forms.DateInput(attrs={"type": "date"}) for f in
                   ["submitted_on", "offer_received_on", "deadline", "visa_applied_on",
                    "biometrics_on", "interview_on", "visa_decision_on"]}


class StageChangeForm(forms.Form):
    stage = forms.ChoiceField(choices=[], widget=forms.Select(
        attrs={"class": "field__input field__select"}))
    note = forms.CharField(required=False, widget=forms.TextInput(
        attrs={"class": "field__input", "placeholder": "Optional note for the record"}))
    notify_student = forms.BooleanField(required=False, initial=True,
                                        label="Notify the student")

    def __init__(self, *args, **kwargs):
        from apps.applications.models import Stage
        super().__init__(*args, **kwargs)
        self.fields["stage"].choices = Stage.choices


class DocumentReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[("verified", "Verify"), ("rejected", "Reject"),
                                          ("reupload", "Request re-upload")])
    remarks = forms.CharField(required=False, max_length=400)


class StaffUserForm(StyledModelForm):
    """SRS FR-USR-01."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role", "is_active"]


class StaffProfileForm(StyledModelForm):
    class Meta:
        model = StaffProfile
        fields = ["designation", "photo", "phone", "bio", "destinations_owned",
                  "is_available", "show_on_website", "display_order"]
        widgets = {"destinations_owned": forms.CheckboxSelectMultiple}


class SiteSettingsForm(StyledModelForm):
    class Meta:
        model = SiteSettings
        exclude = []


class AvailabilityForm(StyledModelForm):
    class Meta:
        model = Availability
        fields = ["counsellor", "weekday", "start_time", "end_time", "slot_minutes",
                  "is_active"]
        widgets = {"start_time": forms.TimeInput(attrs={"type": "time"}),
                   "end_time": forms.TimeInput(attrs={"type": "time"})}


class BlackoutForm(StyledModelForm):
    class Meta:
        model = BlackoutDate
        fields = ["counsellor", "date", "reason"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


def build_form(model_class, exclude=None, widgets=None):
    """Factory used by the generic content CRUD (SRS FR-CMS-01)."""
    meta = type("Meta", (), {
        "model": model_class,
        "exclude": list(exclude or []) + ["created_by", "updated_by"],
        "widgets": widgets or {},
    })
    return type(f"{model_class.__name__}Form", (StyledModelForm,), {"Meta": meta})


DATE_W = forms.DateInput(attrs={"type": "date"})
DATETIME_W = forms.DateTimeInput(attrs={"type": "datetime-local"})

CONTENT_MODELS = {
    "destinations": {
        "model": Country, "label": "Destinations", "icon": "globe",
        "columns": ["name", "code", "currency", "is_active", "display_order"],
        "search": ["name"], "capability": "edit_catalogue",
    },
    "intakes": {
        "model": Intake, "label": "Intakes", "icon": "calendar",
        "columns": ["country", "name", "application_deadline", "is_open"],
        "search": ["name"], "capability": "edit_catalogue",
        "widgets": {"application_deadline": DATE_W},
    },
    "cost-of-living": {
        "model": CostOfLiving, "label": "Cost of living", "icon": "wallet",
        "columns": ["country", "bdt_rate"], "search": [], "capability": "edit_catalogue",
    },
    "visa-requirements": {
        "model": VisaRequirement, "label": "Visa checklist", "icon": "stamp",
        "columns": ["country", "title", "display_order"], "search": ["title"],
        "capability": "edit_catalogue",
    },
    "universities": {
        "model": University, "label": "Universities", "icon": "building",
        "columns": ["name", "country", "city", "world_ranking", "is_partner", "is_active"],
        "search": ["name", "city"], "capability": "edit_catalogue",
    },
    "courses": {
        "model": Course, "label": "Courses", "icon": "book",
        "columns": ["title", "university", "study_level", "tuition_fee", "is_active"],
        "search": ["title"], "capability": "edit_catalogue",
    },
    "scholarships": {
        "model": Scholarship, "label": "Scholarships", "icon": "award",
        "columns": ["title", "country", "award_type", "application_deadline", "is_active"],
        "search": ["title", "provider"], "capability": "edit_catalogue",
        "widgets": {"application_deadline": DATE_W},
    },
    "services": {
        "model": Service, "label": "Services", "icon": "sparkles",
        "columns": ["name", "icon", "is_active", "display_order"], "search": ["name"],
        "capability": "edit_catalogue",
    },
    "service-steps": {
        "model": ServiceStep, "label": "Service steps", "icon": "list",
        "columns": ["service", "number", "title"], "search": ["title"],
        "capability": "edit_catalogue",
    },
    "blog": {
        "model": BlogPost, "label": "Blog posts", "icon": "newspaper",
        "columns": ["title", "category", "status", "published_at", "view_count"],
        "search": ["title"], "capability": "publish_content",
        "widgets": {"published_at": DATETIME_W},
    },
    "blog-categories": {
        "model": Category, "label": "Blog categories", "icon": "folder",
        "columns": ["name", "display_order"], "search": ["name"],
        "capability": "publish_content",
    },
    "blog-tags": {
        "model": Tag, "label": "Blog tags", "icon": "tag", "columns": ["name"],
        "search": ["name"], "capability": "publish_content",
    },
    "events": {
        "model": Event, "label": "Events", "icon": "calendar-days",
        "columns": ["title", "event_type", "start_datetime", "capacity", "status"],
        "search": ["title"], "capability": "publish_content",
        "widgets": {"start_datetime": DATETIME_W, "end_datetime": DATETIME_W,
                    "registration_deadline": DATETIME_W},
    },
    "testimonials": {
        "model": Testimonial, "label": "Testimonials", "icon": "quote",
        "columns": ["student_name", "university", "country", "rating", "is_approved"],
        "search": ["student_name", "university"], "capability": "publish_content",
    },
    "faqs": {
        "model": FAQ, "label": "FAQs", "icon": "help-circle",
        "columns": ["question", "category", "show_on_homepage", "is_active"],
        "search": ["question"], "capability": "publish_content",
    },
    "faq-categories": {
        "model": FAQCategory, "label": "FAQ categories", "icon": "folder",
        "columns": ["name", "display_order"], "search": ["name"],
        "capability": "publish_content",
    },
    "team": {
        "model": TeamMember, "label": "Team members", "icon": "users",
        "columns": ["name", "designation", "display_order", "is_active"],
        "search": ["name"], "capability": "publish_content",
    },
    "pages": {
        "model": Page, "label": "Static pages", "icon": "file",
        "columns": ["title", "slug", "status", "show_in_footer"], "search": ["title"],
        "capability": "publish_content",
    },
    "homepage-sections": {
        "model": HomepageSection, "label": "Homepage sections", "icon": "layout",
        "columns": ["key", "heading", "is_active", "display_order"], "search": [],
        "capability": "publish_content",
    },
    "hero-slides": {
        "model": HeroSlide, "label": "Hero slides", "icon": "image",
        "columns": ["heading", "is_active", "display_order"], "search": ["heading"],
        "capability": "publish_content",
    },
    "why-us": {
        "model": WhyUsPoint, "label": "Why choose us", "icon": "badge-check",
        "columns": ["title", "display_order", "is_active"], "search": ["title"],
        "capability": "publish_content",
    },
    "journey-steps": {
        "model": JourneyStep, "label": "Journey steps", "icon": "route",
        "columns": ["number", "title", "is_active"], "search": ["title"],
        "capability": "publish_content",
    },
    "email-templates": {
        "model": EmailTemplate, "label": "Email templates", "icon": "mail",
        "columns": ["name", "key", "is_active"], "search": ["name"],
        "capability": "site_settings",
    },
}
