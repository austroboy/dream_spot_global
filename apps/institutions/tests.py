"""Course search, filters and shortlist merging (SRS FR-COU-02/07)."""
from django.test import TestCase

from apps.accounts.models import Role, User
from apps.core.models import SiteSettings
from apps.destinations.models import Country
from apps.institutions.models import Course, Shortlist, University


class CourseSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.uk = Country.objects.create(name="United Kingdom", slug="united-kingdom")
        cls.au = Country.objects.create(name="Australia", slug="australia")
        uk_uni = University.objects.create(name="Leeds", slug="leeds", country=cls.uk)
        au_uni = University.objects.create(name="Monash", slug="monash", country=cls.au)
        cls.msc = Course.objects.create(title="MSc Data Science", slug="msc-ds",
                                        university=uk_uni, study_level="master",
                                        discipline="it", tuition_fee=20000)
        cls.bsc = Course.objects.create(title="BSc Nursing", slug="bsc-nursing",
                                        university=au_uni, study_level="bachelor",
                                        discipline="health", tuition_fee=35000)

    def test_filter_by_country(self):
        response = self.client.get("/courses/?country=united-kingdom")
        self.assertContains(response, "MSc Data Science")
        self.assertNotContains(response, "BSc Nursing")

    def test_filter_by_level_and_discipline(self):
        response = self.client.get("/courses/?level=master&discipline=it")
        self.assertContains(response, "MSc Data Science")
        self.assertNotContains(response, "BSc Nursing")

    def test_filter_by_maximum_tuition(self):
        response = self.client.get("/courses/?tuition_max=25000")
        self.assertContains(response, "MSc Data Science")
        self.assertNotContains(response, "BSc Nursing")

    def test_keyword_search_matches_university_name(self):
        response = self.client.get("/courses/?q=Monash")
        self.assertContains(response, "BSc Nursing")

    def test_empty_result_shows_helpful_message(self):
        response = self.client.get("/courses/?q=zzzzzzz")
        self.assertContains(response, "No courses match those filters")

    def test_session_shortlist_merges_into_account_on_login(self):
        self.client.post(f"/shortlist/toggle/{self.msc.pk}/")
        self.assertEqual(Shortlist.objects.filter(user__isnull=True).count(), 1)
        User.objects.create_user(username="u", email="u@x.com", password="Str0ngPass!23",
                                 role=Role.STUDENT)
        self.client.post("/accounts/login/", {"username": "u@x.com",
                                              "password": "Str0ngPass!23"})
        self.assertEqual(Shortlist.objects.filter(user__username="u").count(), 1)  # FR-COU-07
