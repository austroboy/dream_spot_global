"""University and course discovery (SRS 6.3)."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.destinations.models import Country
from apps.institutions.models import DISCIPLINES, STUDY_LEVELS, Course, Shortlist, University
from apps.leads.forms import QuickEnquiryForm

PAGE_SIZE = 12   # SRS FR-COU-04


def _shortlist_filter(request):
    if request.user.is_authenticated:
        return {"user": request.user}
    if not request.session.session_key:
        request.session.save()
    return {"session_key": request.session.session_key}


def shortlisted_course_ids(request):
    return set(Shortlist.objects.filter(**_shortlist_filter(request))
               .exclude(course=None).values_list("course_id", flat=True))


def course_list(request):
    qs = Course.objects.filter(is_active=True).select_related("university",
                                                              "university__country")
    g = request.GET
    country = g.get("country")
    level = g.get("level")
    discipline = g.get("discipline")
    university = g.get("university")
    tuition_max = g.get("tuition_max")
    duration = g.get("duration")
    q = (g.get("q") or "").strip()

    if country:
        qs = qs.filter(university__country__slug=country)
    if level:
        qs = qs.filter(study_level=level)
    if discipline:
        qs = qs.filter(discipline=discipline)
    if university:
        qs = qs.filter(university__slug=university)
    if tuition_max:
        try:
            qs = qs.filter(tuition_fee__lte=int(tuition_max))
        except ValueError:
            pass
    if duration:
        try:
            qs = qs.filter(duration_months__lte=int(duration))
        except ValueError:
            pass
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(university__name__icontains=q))

    sort = g.get("sort", "title")
    qs = qs.order_by({"tuition": "tuition_fee", "-tuition": "-tuition_fee",
                      "ranking": "university__world_ranking"}.get(sort, "title"))

    page = Paginator(qs, PAGE_SIZE).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)

    context = {
        "page_obj": page,
        "total": Paginator(qs, PAGE_SIZE).count,
        "countries": Country.objects.filter(is_active=True)
                     .annotate(n=Count("universities__courses")).filter(n__gt=0),
        "levels": STUDY_LEVELS,
        "disciplines": DISCIPLINES,
        "universities": University.objects.filter(is_active=True)[:80],
        "querystring": params.urlencode(),
        "selected": {"country": country, "level": level, "discipline": discipline,
                     "university": university, "tuition_max": tuition_max,
                     "duration": duration, "q": q, "sort": sort},
        "shortlisted": shortlisted_course_ids(request),
        "meta_title": "Find a Course | Dream Spot Global",
    }
    if request.headers.get("HX-Request"):      # SRS FR-COU-06
        return render(request, "institutions/_course_results.html", context)
    return render(request, "institutions/course_list.html", context)


def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.select_related("university", "university__country")
        .prefetch_related("intakes"), slug=slug, is_active=True)
    similar = Course.objects.filter(is_active=True, discipline=course.discipline) \
        .exclude(pk=course.pk).select_related("university")[:4]
    return render(request, "institutions/course_detail.html", {
        "course": course, "similar": similar, "form": QuickEnquiryForm(),
        "shortlisted": shortlisted_course_ids(request),
        "meta_title": course.meta_title or f"{course.title} — {course.university.name}",
    })


def university_list(request):
    qs = University.objects.filter(is_active=True).select_related("country") \
        .annotate(course_count=Count("courses"))
    g = request.GET
    if g.get("country"):
        qs = qs.filter(country__slug=g["country"])
    if g.get("type"):
        qs = qs.filter(university_type=g["type"])
    if g.get("q"):
        qs = qs.filter(name__icontains=g["q"])
    if g.get("ranking"):
        try:
            qs = qs.filter(world_ranking__lte=int(g["ranking"]))
        except ValueError:
            pass
    qs = qs.order_by("world_ranking", "name")
    page = Paginator(qs, PAGE_SIZE).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    return render(request, "institutions/university_list.html", {
        "page_obj": page,
        "countries": Country.objects.filter(is_active=True),
        "querystring": params.urlencode(),
        "selected": {"country": g.get("country"), "type": g.get("type"),
                     "q": g.get("q"), "ranking": g.get("ranking")},
        "meta_title": "Find a University | Dream Spot Global",
    })


def university_detail(request, slug):
    uni = get_object_or_404(University.objects.select_related("country"), slug=slug,
                            is_active=True)
    return render(request, "institutions/university_detail.html", {
        "university": uni,
        "courses": uni.courses.filter(is_active=True)[:12],
        "scholarships": uni.scholarships.filter(is_active=True)[:4],
        "form": QuickEnquiryForm(initial={"destination": uni.country}),
        "meta_title": uni.meta_title or f"{uni.name} — {uni.country.name}",
    })


@require_POST
def toggle_shortlist(request, pk):
    """SRS FR-COU-07."""
    course = get_object_or_404(Course, pk=pk, is_active=True)
    flt = _shortlist_filter(request)
    obj = Shortlist.objects.filter(course=course, **flt).first()
    if obj:
        obj.delete()
        added = False
    else:
        Shortlist.objects.create(course=course, **flt)
        added = True
    if request.headers.get("HX-Request") or request.headers.get("x-requested-with"):
        return JsonResponse({"added": added, "count": Shortlist.objects.filter(**flt).count()})
    messages.success(request, "Added to your shortlist." if added else "Removed from shortlist.")
    return redirect(request.META.get("HTTP_REFERER", "/courses/"))


def shortlist_view(request):
    items = Shortlist.objects.filter(**_shortlist_filter(request)) \
        .select_related("course", "course__university", "university")
    return render(request, "institutions/shortlist.html", {
        "items": items, "meta_title": "My shortlist"})


def compare_courses(request):
    """SRS FR-COU-08 — up to four courses side by side."""
    ids = [i for i in request.GET.getlist("c") if i.isdigit()][:4]
    courses = Course.objects.filter(pk__in=ids, is_active=True) \
        .select_related("university", "university__country")
    return render(request, "institutions/compare.html", {
        "courses": courses,
        "shortlist": Shortlist.objects.filter(**_shortlist_filter(request))
                     .exclude(course=None).select_related("course"),
        "meta_title": "Compare courses",
    })
