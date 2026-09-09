"""Site-wide behaviour: SEO, redirects, audit trail, maintenance mode."""
from django.test import TestCase

from apps.core.models import AuditLog, Redirect, SiteSettings
from apps.destinations.models import Country


class SiteBehaviourTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSettings.load()
        cls.country = Country.objects.create(name="Ireland", slug="ireland", is_active=True)

    def test_site_settings_is_a_singleton(self):
        second = SiteSettings.load()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(second.pk, self.settings.pk)

    def test_slug_change_creates_a_redirect(self):
        self.country.slug = "republic-of-ireland"
        self.country.save()
        self.assertTrue(Redirect.objects.filter(old_path="/study-abroad/ireland/").exists())

    def test_audit_log_records_model_changes(self):
        AuditLog.objects.all().delete()
        self.country.name = "Ireland (EU)"
        self.country.save()
        self.assertTrue(AuditLog.objects.filter(model_name="Country",
                                                action="update").exists())

    def test_sitemap_and_robots_are_served(self):
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        response = self.client.get("/robots.txt")
        self.assertContains(response, "Disallow: /dashboard/")

    def test_healthcheck_reports_ok(self):
        self.assertJSONEqual(self.client.get("/healthz/").content,
                             {"status": "ok", "database": True})

    def test_maintenance_mode_blocks_public_pages(self):
        self.settings.maintenance_mode = True
        self.settings.save()
        self.assertEqual(self.client.get("/").status_code, 503)
        self.settings.maintenance_mode = False
        self.settings.save()

    def test_missing_page_returns_404(self):
        self.assertEqual(self.client.get("/no-such-page/").status_code, 404)
