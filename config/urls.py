"""Root URL configuration (SRS section 5)."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path

from apps.core import views as core_views
from apps.core.sitemaps import SITEMAPS

urlpatterns = [
    path("django-admin-dsg/", admin.site.urls),          # SRS SEC-14: non-default path

    path("", include("apps.core.urls")),
    path("services/", include("apps.services.urls")),
    path("study-abroad/", include("apps.destinations.urls")),
    path("", include("apps.institutions.urls")),
    path("scholarships/", include("apps.scholarships.urls")),
    path("events/", include("apps.events.urls")),
    path("blog/", include("apps.blog.urls")),
    path("success-stories/", include("apps.testimonials.urls")),
    path("faq/", include("apps.faqs.urls")),
    path("book-counselling/", include("apps.appointments.urls")),
    path("assessment/", include("apps.leads.urls")),

    path("accounts/", include("apps.accounts.urls")),
    path("portal/", include("apps.portal.urls")),
    path("dashboard/", include("apps.dashboard.urls")),

    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", core_views.robots_txt, name="robots"),
    path("healthz/", core_views.healthz, name="healthz"),

    # Generic CMS pages last so they never shadow a real route
    path("<slug:slug>/", core_views.page_detail, name="page_detail"),
]

handler404 = "apps.core.views.handler404"
handler403 = "apps.core.views.handler403"
handler500 = "apps.core.views.handler500"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
elif getattr(settings, "SERVE_MEDIA", False):
    # Uploaded images (logo, hero, blog, country photos) on hosts without a
    # separate media server. Student documents are never served from here —
    # they go through permission-checked views only (SRS SEC-10).
    from django.views.static import serve

    urlpatterns.insert(-1, re_path(
        r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}))
