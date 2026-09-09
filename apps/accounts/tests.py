"""RBAC matrix and authentication tests (SRS QA-03, SEC-08)."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LoginAttempt, Role, StaffProfile, StudentProfile, User
from apps.accounts.permissions import user_can
from apps.core.models import SiteSettings


class PermissionMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in [Role.ADMIN, Role.COUNSELLOR, Role.OFFICER, Role.EDITOR, Role.STUDENT]:
            u = User.objects.create_user(username=role, email=f"{role}@dsg.com",
                                         password="pw", role=role)
            cls.users[role] = u

    def test_admin_has_every_capability(self):
        from apps.accounts.permissions import CAPABILITIES
        for cap in CAPABILITIES:
            self.assertTrue(user_can(self.users[Role.ADMIN], cap), cap)

    def test_counsellor_cannot_verify_documents_or_manage_users(self):
        u = self.users[Role.COUNSELLOR]
        self.assertTrue(user_can(u, "edit_lead"))
        self.assertFalse(user_can(u, "verify_documents"))
        self.assertFalse(user_can(u, "manage_users"))
        self.assertFalse(user_can(u, "view_all_leads"))

    def test_officer_can_verify_but_not_edit_leads(self):
        u = self.users[Role.OFFICER]
        self.assertTrue(user_can(u, "verify_documents"))
        self.assertTrue(user_can(u, "edit_applications"))
        self.assertFalse(user_can(u, "edit_lead"))

    def test_editor_only_touches_content(self):
        u = self.users[Role.EDITOR]
        self.assertTrue(user_can(u, "publish_content"))
        self.assertFalse(user_can(u, "view_students"))
        self.assertFalse(user_can(u, "site_settings"))

    def test_student_has_no_staff_capability(self):
        from apps.accounts.permissions import CAPABILITIES
        for cap in CAPABILITIES:
            self.assertFalse(user_can(self.users[Role.STUDENT], cap), cap)

    def test_anonymous_has_no_capability(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(user_can(AnonymousUser(), "view_own_leads"))


class DashboardAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.editor = User.objects.create_user(username="ed", email="ed@dsg.com",
                                              password="pw", role=Role.EDITOR)
        StaffProfile.objects.create(user=cls.editor)
        cls.student = User.objects.create_user(username="st", email="st@dsg.com",
                                               password="pw", role=Role.STUDENT)
        StudentProfile.objects.create(user=cls.student)

    def test_editor_denied_lead_list(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get("/dashboard/leads/").status_code, 403)

    def test_editor_allowed_blog_crud(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get("/dashboard/content/blog/").status_code, 200)

    def test_student_denied_dashboard(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get("/dashboard/").status_code, 403)

    def test_anonymous_redirected_from_portal(self):
        self.assertEqual(self.client.get("/portal/").status_code, 302)


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.user = User.objects.create_user(username="learner", email="learner@example.com",
                                            password="Str0ngPass!23", role=Role.STUDENT)
        StudentProfile.objects.create(user=cls.user)

    def test_login_with_email(self):
        ok = self.client.login(username="learner@example.com", password="Str0ngPass!23")
        self.assertTrue(ok)

    def test_failed_attempts_are_recorded(self):
        for _ in range(3):
            self.client.post(reverse("accounts:login"),
                             {"username": "learner@example.com", "password": "wrong"})
        self.assertEqual(LoginAttempt.recent_failures("learner@example.com"), 3)

    def test_account_locks_after_five_failures(self):
        for _ in range(6):
            self.client.post(reverse("accounts:login"),
                             {"username": "learner@example.com", "password": "wrong"})
        response = self.client.post(reverse("accounts:login"),
                                    {"username": "learner@example.com",
                                     "password": "Str0ngPass!23"}, follow=True)
        self.assertContains(response, "Too many failed attempts")     # SEC-08

    def test_registration_creates_student_profile(self):
        self.client.post(reverse("accounts:register"), {
            "first_name": "New", "last_name": "Student", "email": "new@example.com",
            "phone": "01712345671", "password1": "Str0ngPass!23",
            "password2": "Str0ngPass!23", "consent": "on"})
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, Role.STUDENT)
        self.assertTrue(hasattr(user, "student_profile"))
