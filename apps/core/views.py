"""Public core views: homepage, about, contact, pages, search (SRS 6.1, 6.12, 6.13)."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog.models import BlogPost
from apps.core.models import (ContactMessage, HeroSlide, HomepageSection, JourneyStep,
                              Page, Redirect, TeamMember, WhyUsPoint)
from apps.core.utils import capture_utm
from apps.destinations.models import Country
from apps.events.models import Event
from apps.faqs.models import FAQ
from apps.institutions.models import Course, University
from apps.leads.forms import EnquiryForm, NewsletterForm, QuickEnquiryForm
from apps.leads.models import NewsletterSubscriber
from apps.leads.services import create_lead
from apps.scholarships.models import Scholarship
from apps.services.models import Service
from apps.testimonials.models import Testimonial


def home(request):
    sections = {s.key: s for s in HomepageSection.objects.filter(is_active=True)}
    ordered = HomepageSection.objects.filter(is_active=True)
    context = {
        "sections": sections,
        "ordered_sections": ordered,
        "slides": HeroSlide.objects.filter(is_active=True),
        "countries": Country.objects.filter(is_active=True, is_featured=True),
        "services": Service.objects.filter(is_active=True, is_featured=True),
        "why_points": WhyUsPoint.objects.filter(is_active=True),
        "journey_steps": JourneyStep.objects.filter(is_active=True),
        "universities": University.objects.filter(is_active=True, is_featured=True)
                                          .select_related("country")[:12],
        "scholarships": Scholarship.objects.filter(is_active=True)
                                           .select_related("country")[:4],
        "events": Event.objects.filter(status="published",
                                       start_datetime__gte=timezone.now())[:3],
        "testimonials": Testimonial.objects.filter(is_approved=True)
                                            .select_related("country")[:8],
        "posts": BlogPost.objects.filter(status="published")
                                 .select_related("category", "author")[:3],
        "faqs": FAQ.objects.filter(is_active=True, show_on_homepage=True)[:6],
        "quick_form": QuickEnquiryForm(),
        "levels": Course._meta.get_field("study_level").choices,
        "disciplines": Course._meta.get_field("discipline").choices,
        "meta_title": "Study Abroad Consultancy in Dhaka | Dream Spot Global",
        "meta_description": ("Free counselling, university admission and student visa guidance "
                             "for the UK, Australia, Canada, USA, Germany, Finland, Ireland and "
                             "New Zealand. Uttara, Dhaka."),
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html", {
        "team": TeamMember.objects.filter(is_active=True),
        "why_points": WhyUsPoint.objects.filter(is_active=True),
        "journey_steps": JourneyStep.objects.filter(is_active=True),
        "testimonials": Testimonial.objects.filter(is_approved=True)[:6],
        "meta_title": "About Dream Spot Global | Study Abroad Consultants in Uttara",
    })


def why_us(request):
    return render(request, "core/why_us.html", {
        "why_points": WhyUsPoint.objects.filter(is_active=True),
        "journey_steps": JourneyStep.objects.filter(is_active=True),
        "meta_title": "Why Choose Dream Spot Global",
    })


def team(request):
    return render(request, "core/team.html", {
        "team": TeamMember.objects.filter(is_active=True),
        "meta_title": "Our Counsellors | Dream Spot Global",
    })


def contact(request):
    form = EnquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lead, created = create_lead(
            data=form.cleaned_data,
            destinations=form.cleaned_data.get("destinations"),
            meta=capture_utm(request), source="contact")
        ContactMessage.objects.create(
            name=form.cleaned_data["full_name"], email=form.cleaned_data["email"],
            phone=form.cleaned_data["phone"], subject="Website contact form",
            message=form.cleaned_data.get("message", ""))
        messages.success(request, "Thank you — our counsellor will contact you within one "
                                  "working day.")
        return redirect("core:thank_you")
    return render(request, "core/contact.html", {
        "form": form,
        "meta_title": "Contact Dream Spot Global | Uttara, Dhaka",
    })


def thank_you(request):
    return render(request, "core/thank_you.html", {"meta_title": "Thank you"})


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, status="published")
    return render(request, "core/page.html", {"page": page, "meta_title": page.title})


def search(request):
    """SRS FR-SRCH-01 — grouped global search."""
    q = (request.GET.get("q") or "").strip()
    results = {}
    if q:
        results = {
            "Courses": Course.objects.filter(is_active=True)
                       .filter(Q(title__icontains=q) | Q(overview__icontains=q))
                       .select_related("university", "university__country")[:8],
            "Universities": University.objects.filter(is_active=True, name__icontains=q)
                            .select_related("country")[:8],
            "Destinations": Country.objects.filter(is_active=True, name__icontains=q)[:8],
            "Scholarships": Scholarship.objects.filter(is_active=True, title__icontains=q)[:8],
            "Events": Event.objects.filter(status="published", title__icontains=q)[:8],
            "Articles": BlogPost.objects.filter(status="published")
                        .filter(Q(title__icontains=q) | Q(excerpt__icontains=q))[:8],
        }
        results = {k: v for k, v in results.items() if v}
    return render(request, "core/search.html", {"q": q, "results": results,
                                                "meta_title": f"Search: {q}" if q else "Search"})


@require_POST
def quick_enquiry(request):
    """Homepage CTA band + sidebar forms (SRS FR-HOM-06)."""
    form = QuickEnquiryForm(request.POST)
    source = request.POST.get("lead_source", "homepage_cta")
    if form.is_valid():
        dest = form.cleaned_data.get("destination")
        create_lead(data=form.cleaned_data, destinations=[dest] if dest else None,
                    meta=capture_utm(request), source=source)
        messages.success(request, "Thank you — we have received your request. "
                                  "A counsellor will call you shortly.")
        return redirect("core:thank_you")
    messages.error(request, "Please check the highlighted fields and try again.")
    return redirect(request.META.get("HTTP_REFERER", "/") + "#enquiry")


@require_POST
def newsletter_signup(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        import secrets
        sub, created = NewsletterSubscriber.objects.get_or_create(
            email=form.cleaned_data["email"],
            defaults={"confirm_token": secrets.token_urlsafe(24)})
        messages.success(request, "Almost there — please confirm the subscription "
                                  "from the email we just sent.")
    else:
        messages.error(request, "Please enter a valid email address.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


def newsletter_confirm(request, token):
    sub = get_object_or_404(NewsletterSubscriber, confirm_token=token)
    sub.is_confirmed = True
    sub.save(update_fields=["is_confirmed"])
    messages.success(request, "Your subscription is confirmed. Welcome aboard!")
    return redirect("core:home")


def maintenance(request):
    return render(request, "core/maintenance.html", status=503)


def robots_txt(request):
    from django.http import HttpResponse
    lines = ["User-agent: *", "Disallow: /dashboard/", "Disallow: /portal/",
             "Disallow: /django-admin/", "Allow: /",
             f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def healthz(request):
    """SRS OPS-07."""
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok})


def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler500(request):
    return render(request, "errors/500.html", status=500)
