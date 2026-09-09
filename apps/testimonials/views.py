from django.core.paginator import Paginator
from django.shortcuts import render

from apps.destinations.models import Country
from apps.testimonials.models import Testimonial


def testimonial_list(request):
    qs = Testimonial.objects.filter(is_approved=True).select_related("country")
    country = request.GET.get("country")
    if country:
        qs = qs.filter(country__slug=country)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "testimonials/list.html", {
        "page_obj": page, "countries": Country.objects.filter(is_active=True),
        "selected_country": country,
        "meta_title": "Student Success Stories | Dream Spot Global",
    })
