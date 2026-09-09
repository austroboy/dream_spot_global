"""Student portal data isolation (SRS FR-STU-14, SEC-10)."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models import Role, StudentProfile, User
from apps.applications.models import Application, Document, Stage
from apps.core.models import SiteSettings
from apps.destinations.models import Country
from apps.institutions.models import Course, University


class PortalIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        country = Country.objects.create(name="Canada", slug="canada")
        uni = University.objects.create(name="UofT", slug="uoft", country=country)
        course = Course.objects.create(title="MSc CS", slug="msc-cs", university=uni,
                                       study_level="master", discipline="it")
        cls.a = StudentProfile.objects.create(user=User.objects.create_user(
            username="a", email="a@x.com", password="pw", role=Role.STUDENT))
        cls.b = StudentProfile.objects.create(user=User.objects.create_user(
            username="b", email="b@x.com", password="pw", role=Role.STUDENT))
        cls.app_b = Application.objects.create(student=cls.b, university=uni, course=course,
                                               stage=Stage.DOCUMENTS)
        cls.doc_b = Document.objects.create(
            student=cls.b, document_type="passport",
            file=SimpleUploadedFile("p.pdf", b"data", content_type="application/pdf"))

    def test_student_cannot_open_another_students_application(self):
        self.client.force_login(self.a.user)
        self.assertEqual(
            self.client.get(f"/portal/applications/{self.app_b.pk}/").status_code, 404)

    def test_student_cannot_download_another_students_document(self):
        self.client.force_login(self.a.user)
        self.assertEqual(
            self.client.get(f"/portal/documents/{self.doc_b.pk}/download/").status_code, 404)

    def test_own_application_is_visible(self):
        self.client.force_login(self.b.user)
        self.assertEqual(
            self.client.get(f"/portal/applications/{self.app_b.pk}/").status_code, 200)

    def test_data_export_only_contains_own_records(self):
        self.client.force_login(self.a.user)
        response = self.client.get("/portal/export/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"b@x.com", response.content)          # PRV-04

    def test_upload_rejects_oversized_file(self):
        self.client.force_login(self.a.user)
        big = SimpleUploadedFile("big.pdf", b"0" * (11 * 1024 * 1024),
                                 content_type="application/pdf")
        self.client.post("/portal/documents/", {"document_type": "passport", "file": big})
        self.assertEqual(Document.objects.filter(student=self.a).count(), 0)   # FR-STU-06

    def test_upload_rejects_disallowed_extension(self):
        self.client.force_login(self.a.user)
        exe = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        self.client.post("/portal/documents/", {"document_type": "other", "file": exe})
        self.assertEqual(Document.objects.filter(student=self.a).count(), 0)
