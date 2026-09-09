"""Destination pages (SRS 6.2)."""
from django.shortcuts import get_object_or_404, render

from apps.destinations.models import Country
from apps.faqs.models import FAQ
from apps.institutions.models import Course, University
from apps.leads.forms import QuickEnquiryForm
from apps.scholarships.models import Scholarship
from apps.testimonials.models import Testimonial


def country_list(request):
    return render(request, "destinations/list.html", {
        "countries": Country.objects.filter(is_active=True),
        "meta_title": "Study Abroad Destinations | Dream Spot Global",
        "meta_description": "Study in the UK, Australia, Canada, USA, Germany, Finland, "
                            "Ireland and New Zealand with expert guidance from Dhaka.",
    })


def country_detail(request, slug):
    country = get_object_or_404(
        Country.objects.prefetch_related("intakes", "visa_items"), slug=slug, is_active=True)
    context = {
        "country": country,
        "cost": getattr(country, "cost", None),
        "universities": University.objects.filter(country=country, is_active=True)[:8],
        "courses": Course.objects.filter(university__country=country, is_active=True)
                                 .select_related("university")[:6],
        "scholarships": Scholarship.objects.filter(country=country, is_active=True)[:4],
        "faqs": FAQ.objects.filter(country=country, is_active=True),
        "testimonials": Testimonial.objects.filter(country=country, is_approved=True)[:3],
        "form": QuickEnquiryForm(initial={"destination": country}),
        "meta_title": country.meta_title or f"Study in {country.name} from Bangladesh",
        "meta_description": country.meta_description or country.tagline,
    }
    return render(request, "destinations/detail.html", context)


def country_universities(request, slug):
    country = get_object_or_404(Country, slug=slug, is_active=True)
    return render(request, "destinations/universities.html", {
        "country": country,
        "universities": University.objects.filter(country=country, is_active=True),
        "meta_title": f"Universities in {country.name}",
    })


def country_cost(request, slug):
    country = get_object_or_404(Country, slug=slug, is_active=True)
    return render(request, "destinations/cost.html", {
        "country": country, "cost": getattr(country, "cost", None),
        "meta_title": f"Cost of living in {country.name}",
    })


def country_visa(request, slug):
    country = get_object_or_404(Country, slug=slug, is_active=True)
    return render(request, "destinations/visa.html", {
        "country": country, "items": country.visa_items.all(),
        "meta_title": f"{country.name} student visa guide",
    })


def compare(request):
    """SRS FR-DST-07 — compare up to three destinations."""
    slugs = [s for s in request.GET.getlist("c") if s][:3]
    selected = list(Country.objects.filter(slug__in=slugs, is_active=True)) if slugs else []
    return render(request, "destinations/compare.html", {
        "all_countries": Country.objects.filter(is_active=True),
        "selected": selected,
        "meta_title": "Compare study destinations",
    })
