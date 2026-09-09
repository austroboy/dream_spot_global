"""Public assessment wizard (SRS 6.7)."""
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core.utils import capture_utm
from apps.destinations.models import Country
from apps.institutions.models import Course
from apps.leads.assessment import assess
from apps.leads.forms import (AssessmentStep1, AssessmentStep2, AssessmentStep3,
                              AssessmentStep4)
from apps.leads.services import create_lead
from apps.notifications.services import send_email

STEPS = {1: AssessmentStep1, 2: AssessmentStep2, 3: AssessmentStep3, 4: AssessmentStep4}
SESSION_KEY = "assessment_data"


def assessment(request, step=1):
    step = max(1, min(4, int(step)))
    data = request.session.get(SESSION_KEY, {})
    FormClass = STEPS[step]

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            cleaned = dict(form.cleaned_data)
            dests = cleaned.pop("destinations", None)
            if dests is not None:
                cleaned["destination_ids"] = [c.pk for c in dests]
            for k, v in list(cleaned.items()):
                if hasattr(v, "isoformat"):
                    cleaned[k] = v.isoformat()
                elif v is not None and not isinstance(v, (str, int, float, bool, list)):
                    cleaned[k] = str(v)
            data.update(cleaned)
            request.session[SESSION_KEY] = data
            request.session.modified = True     # SRS FR-ASM-02: partial progress saved

            if step < 4:
                return redirect("leads:assessment_step", step=step + 1)
            return _finish(request, data)
    else:
        initial = {k: v for k, v in data.items() if k in FormClass.base_fields}
        if step == 4 and data.get("destination_ids"):
            initial["destinations"] = data["destination_ids"]
        form = FormClass(initial=initial)

    return render(request, "leads/assessment.html", {
        "form": form, "step": step, "total_steps": 4,
        "progress": int(step / 4 * 100),
        "meta_title": "Free Profile Assessment | Dream Spot Global",
        "meta_description": "Get a free indicative eligibility assessment for studying "
                            "abroad in under two minutes.",
    })


def _finish(request, data):
    countries = list(Country.objects.filter(pk__in=data.get("destination_ids", [])))
    result = assess(
        destinations=countries,
        study_level=data.get("study_level", ""),
        gpa=data.get("gpa"),
        english_test=data.get("english_test", "none"),
        english_score=data.get("english_score"),
        work_experience_years=data.get("work_experience_years") or 0,
        has_visa_refusal=bool(data.get("has_visa_refusal")),
        backlogs=data.get("backlogs") or 0,
    )
    lead, _ = create_lead(
        data={**data, "assessment_result": result, "consent_given": True},
        destinations=countries, meta=capture_utm(request), source="assessment")

    recommended = Course.objects.filter(
        is_active=True, university__country__in=countries,
        study_level=data.get("study_level", "")).select_related("university")[:6]

    send_email(
        subject="Your free profile assessment — Dream Spot Global",
        to=lead.email,
        body=("Dear {name},\n\nYour indicative eligibility score is {score}/100.\n"
              "Matched destinations: {matched}\nNext steps:\n{actions}\n\n"
              "Dream Spot Global").format(
                  name=lead.full_name, score=result["eligibility_score"],
                  matched=", ".join(result["matched_destinations"]) or "To be reviewed",
                  actions="\n".join("- " + a for a in result["recommended_actions"])))

    request.session.pop(SESSION_KEY, None)
    return render(request, "leads/assessment_result.html", {
        "result": result, "lead": lead, "recommended": recommended,
        "meta_title": "Your assessment result",
    })
