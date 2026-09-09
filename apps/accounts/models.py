"""Users, roles and profiles (SRS 2.4, 9.1, 12.2)."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Role(models.TextChoices):
    ADMIN = "admin", "Administrator"
    COUNSELLOR = "counsellor", "Counsellor"
    OFFICER = "officer", "Application Officer"
    EDITOR = "editor", "Content Editor"
    STUDENT = "student", "Student"


class User(AbstractUser):
    """SRS FR-STU-01 — email is the login identifier."""
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT,
                            db_index=True)
    phone = models.CharField(max_length=32, blank=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

    # --- role helpers used by RBAC decorators (SRS 12.2) --------------------
    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_counsellor(self):
        return self.role == Role.COUNSELLOR

    @property
    def is_officer(self):
        return self.role == Role.OFFICER

    @property
    def is_editor(self):
        return self.role == Role.EDITOR

    @property
    def is_student(self):
        return self.role == Role.STUDENT

    @property
    def is_staff_member(self):
        return self.role in {Role.ADMIN, Role.COUNSELLOR, Role.OFFICER, Role.EDITOR} \
            or self.is_superuser

    @property
    def display_role(self):
        return "Superuser" if self.is_superuser and self.role != Role.ADMIN \
            else self.get_role_display()

    def initials(self):
        parts = [p for p in [self.first_name, self.last_name] if p]
        if parts:
            return "".join(p[0] for p in parts).upper()[:2]
        return (self.username or "?")[:2].upper()


class StaffProfile(TimeStampedModel):
    """SRS 9.1 — counsellor / officer / editor record."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    designation = models.CharField(max_length=120, blank=True)
    photo = models.ImageField(upload_to="staff/", blank=True, null=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    destinations_owned = models.ManyToManyField("destinations.Country", blank=True,
                                                related_name="owning_staff")
    is_available = models.BooleanField(default=True)
    show_on_website = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "user__first_name"]

    def __str__(self):
        return f"{self.user} ({self.designation or self.user.get_role_display()})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def open_lead_count(self):
        return self.leads.exclude(status__in=["converted", "lost", "invalid",
                                              "not_interested"]).count()


class StudentProfile(TimeStampedModel):
    """SRS FR-STU-04 — the applicant record behind the portal."""
    GENDER = [("male", "Male"), ("female", "Female"), ("other", "Other")]
    ENGLISH_TESTS = [("none", "Not taken"), ("ielts", "IELTS"), ("pte", "PTE"),
                     ("toefl", "TOEFL"), ("duolingo", "Duolingo"), ("moi", "MOI")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="converted_students")

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER, blank=True)
    nationality = models.CharField(max_length=80, blank=True, default="Bangladeshi")
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    # SRS PRV-06: sensitive identifier, encrypt at rest in production
    passport_no = models.CharField(max_length=40, blank=True)
    passport_expiry = models.DateField(null=True, blank=True)

    current_education = models.CharField(max_length=160, blank=True)
    institution_name = models.CharField(max_length=180, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    year_of_passing = models.PositiveIntegerField(null=True, blank=True)

    english_test = models.CharField(max_length=12, choices=ENGLISH_TESTS, default="none")
    english_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    english_test_date = models.DateField(null=True, blank=True)

    work_experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    has_visa_refusal = models.BooleanField(default=False)
    visa_refusal_note = models.TextField(blank=True)

    preferred_destinations = models.ManyToManyField("destinations.Country", blank=True,
                                                    related_name="interested_students")
    preferred_intake = models.CharField(max_length=40, blank=True)
    preferred_level = models.CharField(max_length=40, blank=True)
    budget_bdt = models.PositiveIntegerField(null=True, blank=True)

    assigned_counsellor = models.ForeignKey(StaffProfile, null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name="students")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.get_full_name() or self.user.email

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def completeness(self):
        """SRS FR-APP-01 — profile completeness percentage."""
        fields = [self.date_of_birth, self.gender, self.address, self.passport_no,
                  self.current_education, self.gpa, self.english_test != "none",
                  self.preferred_intake, self.preferred_level]
        filled = sum(1 for f in fields if f)
        filled += 1 if self.preferred_destinations.exists() else 0
        return int(round(filled / (len(fields) + 1) * 100))


class AcademicRecord(TimeStampedModel):
    """SRS FR-STU-04 — multiple academic history entries."""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                related_name="academic_records")
    level = models.CharField(max_length=80)
    institution = models.CharField(max_length=180)
    board_or_university = models.CharField(max_length=180, blank=True)
    result = models.CharField(max_length=40, blank=True)
    passing_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-passing_year"]

    def __str__(self):
        return f"{self.level} — {self.institution}"


class LoginAttempt(models.Model):
    """SRS SEC-08 — rate limiting evidence."""
    identifier = models.CharField(max_length=180, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def recent_failures(cls, identifier, minutes=15):
        since = timezone.now() - timezone.timedelta(minutes=minutes)
        return cls.objects.filter(identifier=identifier, successful=False,
                                  created_at__gte=since).count()
