"""XML sitemap (SRS SEO-03)."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import BlogPost
from apps.core.models import Page
from apps.destinations.models import Country
from apps.events.models import Event
from apps.institutions.models import Course, University
from apps.scholarships.models import Scholarship
from apps.services.models import Service


class StaticSitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return ["core:home", "core:about", "core:why_us", "core:team", "core:contact",
                "services:list", "destinations:list", "institutions:course_list",
                "institutions:university_list", "scholarships:list", "events:list",
                "blog:list", "testimonials:list", "faqs:list",
                "appointments:book", "leads:assessment"]

    def location(self, item):
        return reverse(item)


class ModelSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    model = None
    filters = {}

    def items(self):
        return self.model.objects.filter(**self.filters)

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None)


class CountrySitemap(ModelSitemap):
    model = Country
    filters = {"is_active": True}
    priority = 0.9


class ServiceSitemap(ModelSitemap):
    model = Service
    filters = {"is_active": True}


class UniversitySitemap(ModelSitemap):
    model = University
    filters = {"is_active": True}


class CourseSitemap(ModelSitemap):
    model = Course
    filters = {"is_active": True}
    priority = 0.6


class ScholarshipSitemap(ModelSitemap):
    model = Scholarship
    filters = {"is_active": True}


class EventSitemap(ModelSitemap):
    model = Event
    filters = {"status": "published"}


class BlogSitemap(ModelSitemap):
    model = BlogPost
    filters = {"status": "published"}


class PageSitemap(ModelSitemap):
    model = Page
    filters = {"status": "published"}


SITEMAPS = {
    "static": StaticSitemap, "destinations": CountrySitemap, "services": ServiceSitemap,
    "universities": UniversitySitemap, "courses": CourseSitemap,
    "scholarships": ScholarshipSitemap, "events": EventSitemap,
    "blog": BlogSitemap, "pages": PageSitemap,
}
