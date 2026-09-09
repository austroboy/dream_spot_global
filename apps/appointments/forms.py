from django import forms

from apps.accounts.models import Role, StaffProfile
from apps.appointments.models import Appointment
from apps.core.validators import validate_bd_phone
from apps.destinations.models import Country
from apps.leads.forms import BaseStyledForm, HoneypotMixin


class AppointmentForm(HoneypotMixin, BaseStyledForm, forms.ModelForm):
    phone = forms.CharField(max_length=32, validators=[validate_bd_phone], label="Mobile number")
    slot = forms.CharField(widget=forms.HiddenInput)
    consent_given = forms.BooleanField(
        required=True, label="I agree to be contacted and accept the Privacy Policy.")

    class Meta:
        model = Appointment
        fields = ["full_name", "email", "phone", "destination", "mode", "notes"]
        labels = {"full_name": "Full name", "destination": "Destination of interest",
                  "mode": "How would you like to meet?", "notes": "Anything we should know?"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination"].queryset = Country.objects.filter(is_active=True)
        self.fields["destination"].required = False
        self.fields["counsellor"] = forms.ModelChoiceField(
            queryset=StaffProfile.objects.filter(user__role=Role.COUNSELLOR,
                                                 user__is_active=True, is_available=True),
            required=False, empty_label="Any available counsellor", label="Counsellor")
        self.fields["counsellor"].widget.attrs["class"] = "field__input field__select"


class RescheduleForm(BaseStyledForm):
    slot = forms.CharField(widget=forms.HiddenInput)
