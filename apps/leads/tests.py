"""Lead capture, deduplication, assignment and conversion (SRS QA-01, QA-02)."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, StaffProfile, StudentProfile, User
from apps.core.models import SiteSettings
from apps.destinations.models import Country
from apps.leads.assessment import assess
from apps.leads.models import Lead, LeadStatus
from apps.leads.services import convert_lead, create_lead


class LeadCaptureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.uk = Country.objects.create(name="United Kingdom", slug="united-kingdom")
        cls.counsellor_user = User.objects.create_user(
            username="c1", email="c1@dsg.com", password="x", role=Role.COUNSELLOR)
        cls.counsellor = StaffProfile.objects.create(user=cls.counsellor_user)

    def _payload(self, **over):
        data = {"full_name": "Test Student", "phone": "01712345678",
                "email": "test@example.com", "destination": self.uk.pk,
                "consent_given": "on"}
        data.update(over)
        return data

    def test_enquiry_creates_lead_and_assigns_counsellor(self):
        self.client.post(reverse("core:quick_enquiry"), self._payload())
        lead = Lead.objects.get(email="test@example.com")
        self.assertEqual(lead.assigned_to, self.counsellor)      # FR-LDM-04
        self.assertEqual(lead.status, LeadStatus.NEW)
        self.assertTrue(lead.activities.filter(activity_type="created").exists())

    def test_phone_is_normalised_to_e164(self):
        self.client.post(reverse("core:quick_enquiry"), self._payload())
        self.assertEqual(Lead.objects.get(email="test@example.com").phone, "+8801712345678")

    def test_duplicate_within_window_is_merged(self):
        self.client.post(reverse("core:quick_enquiry"), self._payload())
        self.client.post(reverse("core:quick_enquiry"), self._payload())
        self.assertEqual(Lead.objects.filter(email="test@example.com").count(), 1)  # FR-LED-07
        lead = Lead.objects.get(email="test@example.com")
        self.assertTrue(lead.activities.filter(activity_type="enquiry").exists())

    def test_honeypot_blocks_submission(self):
        self.client.post(reverse("core:quick_enquiry"),
                         self._payload(website="http://spam.example"))
        self.assertFalse(Lead.objects.exists())                  # FR-LED-05

    def test_invalid_bangladeshi_phone_rejected(self):
        self.client.post(reverse("core:quick_enquiry"), self._payload(phone="12345"))
        self.assertFalse(Lead.objects.exists())                  # FR-LED-04

    def test_consent_is_required(self):
        payload = self._payload()
        payload.pop("consent_given")
        self.client.post(reverse("core:quick_enquiry"), payload)
        self.assertFalse(Lead.objects.exists())                  # PRV-01

    def test_conversion_creates_student_portal_account(self):
        lead, _ = create_lead(data={"full_name": "Convert Me", "email": "conv@example.com",
                                    "phone": "01712345600"},
                              destinations=[self.uk], source="contact")
        profile, password = convert_lead(lead)
        lead.refresh_from_db()
        self.assertIsInstance(profile, StudentProfile)           # FR-LDM-06
        self.assertEqual(lead.status, LeadStatus.CONVERTED)
        self.assertTrue(profile.user.check_password(password))
        self.assertIn(self.uk, profile.preferred_destinations.all())


class AssessmentEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uk = Country.objects.create(name="United Kingdom", slug="united-kingdom")
        cls.de = Country.objects.create(name="Germany", slug="germany")

    def test_strong_profile_matches_destinations(self):
        result = assess(destinations=[self.uk], study_level="master", gpa=3.8,
                        english_test="ielts", english_score=7.0, work_experience_years=2)
        self.assertIn("United Kingdom", result["matched_destinations"])
        self.assertGreaterEqual(result["eligibility_score"], 70)

    def test_low_english_flags_country_for_review(self):
        result = assess(destinations=[self.de], study_level="master", gpa=3.0,
                        english_test="ielts", english_score=5.0)
        self.assertIn("Germany", result["needs_review"])          # FR-ASM-03

    def test_visa_refusal_lowers_score_and_adds_action(self):
        base = assess(destinations=[self.uk], study_level="master", gpa=3.5,
                      english_test="ielts", english_score=6.5)
        refused = assess(destinations=[self.uk], study_level="master", gpa=3.5,
                         english_test="ielts", english_score=6.5, has_visa_refusal=True)
        self.assertLess(refused["eligibility_score"], base["eligibility_score"])
        self.assertTrue(any("refusal" in a for a in refused["recommended_actions"]))

    def test_score_is_always_bounded(self):
        worst = assess(destinations=[], study_level="master", has_visa_refusal=True)
        self.assertGreaterEqual(worst["eligibility_score"], 15)
        self.assertLessEqual(worst["eligibility_score"], 95)
