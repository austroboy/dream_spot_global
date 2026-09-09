from django.shortcuts import get_object_or_404, render

from apps.destinations.models import Country
from apps.faqs.models import FAQ
from apps.leads.forms import QuickEnquiryForm
from apps.services.models import Service


def service_list(request):
    return render(request, "services/list.html", {
        "services": Service.objects.filter(is_active=True),
        "meta_title": "Our Services | Dream Spot Global",
        "meta_description": "Free counselling, profile assessment, course and university "
                            "selection, application processing, scholarships, SOP/LOR, visa "
                            "guidance and pre-departure support.",
    })


def service_detail(request, slug):
    service = get_object_or_404(Service.objects.prefetch_related("steps"), slug=slug,
                                is_active=True)
    return render(request, "services/detail.html", {
        "service": service,
        "faqs": FAQ.objects.filter(service=service, is_active=True),
        "countries": service.related_countries.all() or Country.objects.filter(is_active=True),
        "form": QuickEnquiryForm(),
        "meta_title": service.meta_title or f"{service.name} | Dream Spot Global",
        "meta_description": service.meta_description or service.short_description,
    })
