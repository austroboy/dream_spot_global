"""Application reference numbers, progress and stage history (SRS FR-APP-02/03)."""
from django.test import TestCase

from apps.accounts.models import Role, StudentProfile, User
from apps.applications.models import STAGE_ORDER, Application, Stage
from apps.destinations.models import Country
from apps.institutions.models import Course, University


class ApplicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        country = Country.objects.create(name="Australia", slug="australia")
        cls.uni = University.objects.create(name="Monash", slug="monash", country=country)
        cls.course = Course.objects.create(title="MBA", slug="mba", university=cls.uni,
                                           study_level="master", discipline="business")
        cls.student = StudentProfile.objects.create(user=User.objects.create_user(
            username="s", email="s@x.com", password="pw", role=Role.STUDENT))

    def _make(self):
        return Application.objects.create(student=self.student, university=self.uni,
                                          course=self.course)

    def test_reference_number_is_generated_and_sequential(self):
        first, second = self._make(), self._make()
        self.assertTrue(first.reference_no.startswith("DSG-"))
        self.assertNotEqual(first.reference_no, second.reference_no)
        self.assertEqual(int(second.reference_no.split("-")[-1]),
                         int(first.reference_no.split("-")[-1]) + 1)

    def test_progress_reflects_stage_position(self):
        app = self._make()
        self.assertLess(app.progress_percent, 20)
        app.stage = Stage.DEPARTED
        self.assertEqual(app.progress_percent, 100)

    def test_timeline_marks_exactly_one_current_stage(self):
        app = self._make()
        app.stage = Stage.OFFER_RECEIVED
        timeline = app.timeline()
        self.assertEqual(len(timeline), len(STAGE_ORDER))
        self.assertEqual(sum(1 for s in timeline if s["current"]), 1)
        self.assertTrue(timeline[0]["done"])

    def test_soft_delete_hides_from_default_manager(self):
        app = self._make()
        app.soft_delete()
        self.assertFalse(Application.objects.filter(pk=app.pk).exists())
        self.assertTrue(Application.all_objects.filter(pk=app.pk).exists())
