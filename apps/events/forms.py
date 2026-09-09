from django import forms

from apps.core.validators import validate_bd_phone
from apps.destinations.models import Country
from apps.events.models import EventRegistration
from apps.leads.forms import BaseStyledForm, HoneypotMixin


class EventRegistrationForm(HoneypotMixin, BaseStyledForm, forms.ModelForm):
    phone = forms.CharField(max_length=32, validators=[validate_bd_phone],
                            label="Mobile number")
    consent_given = forms.BooleanField(
        required=True, label="I agree to be contacted about this event.")

    class Meta:
        model = EventRegistration
        fields = ["full_name", "email", "phone", "destination_interest", "study_level"]
        labels = {"full_name": "Full name", "destination_interest": "Destination of interest",
                  "study_level": "Study level"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination_interest"].queryset = Country.objects.filter(is_active=True)
        self.fields["destination_interest"].required = False
        self.fields["study_level"].required = False
