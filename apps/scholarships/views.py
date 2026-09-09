from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.destinations.models import Country
from apps.leads.forms import QuickEnquiryForm
from apps.scholarships.models import Scholarship


def scholarship_list(request):
    qs = Scholarship.objects.filter(is_active=True).select_related("country", "university")
    g = request.GET
    if g.get("country"):
        qs = qs.filter(country__slug=g["country"])
    if g.get("level"):
        qs = qs.filter(study_level__icontains=g["level"])
    if g.get("award"):
        qs = qs.filter(award_type=g["award"])
    if g.get("deadline") == "30":
        qs = qs.filter(application_deadline__lte=timezone.localdate()
                       + timezone.timedelta(days=30))
    if not g.get("show_expired"):
        qs = qs.exclude(application_deadline__lt=timezone.localdate())   # SRS FR-SCH-03
    page = Paginator(qs, 12).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    return render(request, "scholarships/list.html", {
        "page_obj": page,
        "countries": Country.objects.filter(is_active=True),
        "award_types": Scholarship.AWARD_TYPES,
        "querystring": params.urlencode(),
        "selected": {"country": g.get("country"), "award": g.get("award"),
                     "level": g.get("level"), "deadline": g.get("deadline")},
        "meta_title": "Scholarships for Bangladeshi Students | Dream Spot Global",
    })


def scholarship_detail(request, slug):
    s = get_object_or_404(Scholarship.objects.select_related("country", "university"),
                          slug=slug, is_active=True)
    return render(request, "scholarships/detail.html", {
        "scholarship": s, "form": QuickEnquiryForm(initial={"destination": s.country}),
        "related": Scholarship.objects.filter(is_active=True, country=s.country)
                   .exclude(pk=s.pk)[:3],
        "meta_title": s.meta_title or s.title,
    })
