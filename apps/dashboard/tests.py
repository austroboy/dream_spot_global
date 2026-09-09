"""Dashboard scoping, bulk actions and reports (SRS 8.2, 12.2)."""
from django.test import TestCase

from apps.accounts.models import Role, StaffProfile, User
from apps.core.models import SiteSettings
from apps.leads.models import Lead, LeadStatus


class LeadScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.admin = User.objects.create_user(username="admin", email="a@dsg.com",
                                             password="pw", role=Role.ADMIN)
        u1 = User.objects.create_user(username="c1", email="c1@dsg.com", password="pw",
                                      role=Role.COUNSELLOR)
        u2 = User.objects.create_user(username="c2", email="c2@dsg.com", password="pw",
                                      role=Role.COUNSELLOR)
        cls.c1 = StaffProfile.objects.create(user=u1)
        cls.c2 = StaffProfile.objects.create(user=u2)
        cls.mine = Lead.objects.create(full_name="Mine", email="m@x.com",
                                       phone="+8801711111111", assigned_to=cls.c1)
        cls.theirs = Lead.objects.create(full_name="Theirs", email="t@x.com",
                                         phone="+8801722222222", assigned_to=cls.c2)

    def test_counsellor_sees_only_their_own_leads(self):
        self.client.force_login(self.c1.user)
        response = self.client.get("/dashboard/leads/")
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Theirs")

    def test_admin_sees_every_lead(self):
        self.client.force_login(self.admin)
        response = self.client.get("/dashboard/leads/")
        self.assertContains(response, "Mine")
        self.assertContains(response, "Theirs")

    def test_counsellor_cannot_open_another_counsellors_lead(self):
        self.client.force_login(self.c1.user)
        self.assertEqual(self.client.get(f"/dashboard/leads/{self.theirs.pk}/").status_code,
                         404)

    def test_counsellor_cannot_reassign(self):
        self.client.force_login(self.c1.user)
        response = self.client.post(f"/dashboard/leads/{self.mine.pk}/",
                                    {"action": "assign", "assigned_to": self.c2.pk})
        self.assertEqual(response.status_code, 403)              # FR-LDM-04
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.assigned_to, self.c1)

    def test_admin_bulk_status_change(self):
        self.client.force_login(self.admin)
        self.client.post("/dashboard/leads/bulk/", {
            "selected": [self.mine.pk, self.theirs.pk],
            "bulk_action": "status", "bulk_status": LeadStatus.CONTACTED})
        self.mine.refresh_from_db()
        self.theirs.refresh_from_db()
        self.assertEqual(self.mine.status, LeadStatus.CONTACTED)  # FR-LDM-07
        self.assertEqual(self.theirs.status, LeadStatus.CONTACTED)

    def test_csv_export_returns_a_file(self):
        self.client.force_login(self.admin)
        response = self.client.get("/dashboard/leads/?export=csv")
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_charts_endpoint_returns_json(self):
        self.client.force_login(self.admin)
        data = self.client.get("/dashboard/charts.json").json()
        for key in ("by_day", "by_source", "funnel", "counsellors"):
            self.assertIn(key, data)

    def test_reports_page_renders_for_admin(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/dashboard/reports/").status_code, 200)
