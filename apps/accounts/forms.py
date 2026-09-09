"""Registration, login and profile forms (SRS 7)."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError

from apps.accounts.models import AcademicRecord, Role, StudentProfile, User
from apps.core.validators import validate_bd_phone
from apps.leads.forms import BaseStyledForm


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "field__checkbox"
            elif isinstance(w, forms.CheckboxSelectMultiple):
                w.attrs["class"] = "field__chips"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = "field__input field__select"
            elif isinstance(w, forms.Textarea):
                w.attrs["class"] = "field__input field__textarea"
                w.attrs.setdefault("rows", 4)
            elif isinstance(w, (forms.DateInput,)):
                w.attrs["class"] = "field__input"
                w.input_type = "date"
            else:
                w.attrs["class"] = "field__input"


class RegistrationForm(BaseStyledForm):
    first_name = forms.CharField(max_length=60, label="First name")
    last_name = forms.CharField(max_length=60, required=False, label="Last name")
    email = forms.EmailField(label="Email address")
    phone = forms.CharField(max_length=20, validators=[validate_bd_phone],
                            label="Mobile number")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password",
                                min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    consent = forms.BooleanField(label="I accept the Privacy Policy and Terms of Use.")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def save(self):
        import secrets
        data = self.cleaned_data
        base = data["email"].split("@")[0][:24]
        username = base
        i = 2
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1
        user = User.objects.create_user(
            username=username, email=data["email"], password=data["password1"],
            first_name=data["first_name"], last_name=data.get("last_name", ""),
            role=Role.STUDENT, phone=data["phone"])
        user.verification_token = secrets.token_urlsafe(32)
        user.save(update_fields=["verification_token"])
        StudentProfile.objects.create(user=user)
        return user


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email or username"
        for f in self.fields.values():
            f.widget.attrs["class"] = "field__input"


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs["class"] = "field__input"


class StudentProfileForm(StyledModelForm):
    class Meta:
        model = StudentProfile
        fields = ["date_of_birth", "gender", "nationality", "address", "city",
                  "passport_no", "passport_expiry", "current_education", "institution_name",
                  "gpa", "year_of_passing", "english_test", "english_score",
                  "english_test_date", "work_experience_years", "has_visa_refusal",
                  "visa_refusal_note", "preferred_destinations", "preferred_intake",
                  "preferred_level", "budget_bdt"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "passport_expiry": forms.DateInput(attrs={"type": "date"}),
            "english_test_date": forms.DateInput(attrs={"type": "date"}),
            "preferred_destinations": forms.CheckboxSelectMultiple,
        }


class UserDetailsForm(StyledModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar"]


class AcademicRecordForm(StyledModelForm):
    class Meta:
        model = AcademicRecord
        fields = ["level", "institution", "board_or_university", "result", "passing_year"]
