"""Public lead-capture forms (SRS 6.6, 6.7)."""
from django import forms

from apps.core.validators import validate_bd_phone
from apps.destinations.models import Country
from apps.leads.models import ENGLISH_TESTS, INTAKES, STUDY_LEVELS


class HoneypotMixin(forms.Form):
    """SRS FR-LED-05 — honeypot; real users never fill this."""
    website = forms.CharField(required=False, widget=forms.HiddenInput,
                              label="Leave this empty")

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class BaseStyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "field__input"
            if isinstance(field.widget, forms.Select):
                css = "field__input field__select"
            elif isinstance(field.widget, forms.Textarea):
                css = "field__input field__textarea"
                field.widget.attrs.setdefault("rows", 4)
            elif isinstance(field.widget, forms.CheckboxInput):
                css = "field__checkbox"
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                css = "field__chips"
            field.widget.attrs["class"] = css
            if field.required and not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["required"] = "required"


class QuickEnquiryForm(HoneypotMixin, BaseStyledForm):
    """Short inline form used in the homepage CTA band and sidebars."""
    full_name = forms.CharField(max_length=120, label="Full name",
                                widget=forms.TextInput(attrs={"placeholder": "Your full name"}))
    phone = forms.CharField(max_length=20, validators=[validate_bd_phone], label="Mobile number",
                            widget=forms.TextInput(attrs={"placeholder": "01XXXXXXXXX"}))
    email = forms.EmailField(label="Email",
                             widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}))
    destination = forms.ModelChoiceField(queryset=Country.objects.filter(is_active=True),
                                         required=False, label="Preferred destination",
                                         empty_label="Select a destination")
    consent_given = forms.BooleanField(
        required=True, label="I agree to be contacted and accept the Privacy Policy.")


class EnquiryForm(HoneypotMixin, BaseStyledForm):
    """SRS FR-LED-02 — the full standard enquiry."""
    full_name = forms.CharField(max_length=120, label="Full name")
    email = forms.EmailField(label="Email address")
    phone = forms.CharField(max_length=20, validators=[validate_bd_phone], label="Mobile number")
    destinations = forms.ModelMultipleChoiceField(
        queryset=Country.objects.filter(is_active=True), required=False,
        widget=forms.CheckboxSelectMultiple, label="Preferred destination(s)")
    study_level = forms.ChoiceField(choices=[("", "Select level")] + STUDY_LEVELS,
                                    required=False, label="Study level")
    intended_intake = forms.ChoiceField(choices=[("", "Select intake")] + INTAKES,
                                        required=False, label="Intended intake")
    last_qualification = forms.CharField(max_length=160, required=False,
                                         label="Last qualification")
    english_test = forms.ChoiceField(choices=ENGLISH_TESTS, required=False,
                                     label="English test", initial="none")
    english_score = forms.DecimalField(required=False, max_digits=4, decimal_places=1,
                                       label="Score (if any)")
    message = forms.CharField(widget=forms.Textarea, required=False, label="Your message")
    consent_given = forms.BooleanField(
        required=True, label="I agree to be contacted and accept the Privacy Policy.")


class NewsletterForm(BaseStyledForm):
    email = forms.EmailField(label="", widget=forms.EmailInput(
        attrs={"placeholder": "Enter your email"}))


# --- Free profile assessment wizard (SRS 6.7) ------------------------------
class AssessmentStep1(HoneypotMixin, BaseStyledForm):
    full_name = forms.CharField(max_length=120, label="Full name")
    email = forms.EmailField(label="Email address")
    phone = forms.CharField(max_length=20, validators=[validate_bd_phone], label="Mobile number")
    city = forms.CharField(max_length=80, required=False, label="City")


class AssessmentStep2(BaseStyledForm):
    last_qualification = forms.CharField(max_length=160, label="Last qualification")
    institution_name = forms.CharField(max_length=180, required=False, label="Institution")
    gpa = forms.DecimalField(max_digits=4, decimal_places=2, required=False,
                             label="Result / GPA (out of 5 or 4)")
    year_of_passing = forms.IntegerField(required=False, label="Year of passing")
    backlogs = forms.IntegerField(required=False, initial=0, label="Number of backlogs")


class AssessmentStep3(BaseStyledForm):
    english_test = forms.ChoiceField(choices=ENGLISH_TESTS, label="English test", initial="none")
    english_score = forms.DecimalField(max_digits=4, decimal_places=1, required=False,
                                       label="Overall score")
    work_experience_years = forms.DecimalField(max_digits=4, decimal_places=1, required=False,
                                               initial=0, label="Work experience (years)")
    has_visa_refusal = forms.BooleanField(required=False, label="I have a previous visa refusal")


class AssessmentStep4(BaseStyledForm):
    destinations = forms.ModelMultipleChoiceField(
        queryset=Country.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple, label="Preferred destination(s)")
    study_level = forms.ChoiceField(choices=STUDY_LEVELS, label="Intended study level")
    intended_intake = forms.ChoiceField(choices=INTAKES, label="Intended intake")
    budget_bdt = forms.IntegerField(required=False, label="Yearly budget (BDT)")
    consent_given = forms.BooleanField(
        required=True, label="I agree to be contacted and accept the Privacy Policy.")
