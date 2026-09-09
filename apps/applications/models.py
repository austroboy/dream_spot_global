"""Applications, documents and visa tracking (SRS 6.x, 7, 8.3)."""
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Stage(models.TextChoices):
    """SRS FR-STU-07 — the twelve-stage pipeline."""
    ENQUIRY = "enquiry", "Enquiry"
    COUNSELLING = "counselling", "Counselling"
    DOCUMENTS = "documents", "Documents"
    UNIVERSITY_APPLICATION = "university_application", "University application"
    OFFER_RECEIVED = "offer_received", "Offer received"
    OFFER_ACCEPTED = "offer_accepted", "Offer accepted"
    DEPOSIT_PAID = "deposit_paid", "Tuition / deposit paid"
    CAS_ISSUED = "cas_issued", "CAS / I-20 / COE issued"
    VISA_APPLIED = "visa_applied", "Visa application"
    VISA_GRANTED = "visa_granted", "Visa granted"
    PRE_DEPARTURE = "pre_departure", "Pre-departure"
    DEPARTED = "departed", "Departed"


STAGE_ORDER = [s for s, _ in Stage.choices]

DOCUMENT_TYPES = [
    ("passport", "Passport"), ("transcript", "Academic transcript"),
    ("certificate", "Academic certificate"), ("english_test", "IELTS / PTE scorecard"),
    ("sop", "Statement of Purpose"), ("lor", "Letter of Recommendation"),
    ("cv", "CV / Résumé"), ("bank_statement", "Bank statement"),
    ("photograph", "Photograph"), ("experience", "Experience letter"),
    ("other", "Other"),
]


class Application(SoftDeleteModel):
    STATUS_VISA = [("not_applied", "Not applied"), ("applied", "Applied"),
                   ("biometrics", "Biometrics done"), ("interview", "Interview scheduled"),
                   ("granted", "Granted"), ("refused", "Refused")]

    reference_no = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE,
                                related_name="applications")
    university = models.ForeignKey("institutions.University", on_delete=models.PROTECT,
                                   related_name="applications")
    course = models.ForeignKey("institutions.Course", on_delete=models.PROTECT,
                               related_name="applications")
    intake = models.CharField(max_length=40, blank=True)
    study_level = models.CharField(max_length=20, blank=True)

    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.ENQUIRY,
                             db_index=True)
    sub_status = models.CharField(max_length=120, blank=True)
    priority = models.CharField(max_length=10, default="medium",
                                choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")])
    assigned_officer = models.ForeignKey("accounts.StaffProfile", null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         related_name="applications")

    application_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tuition_deposit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    offer_type = models.CharField(max_length=20, blank=True,
                                  choices=[("conditional", "Conditional"),
                                           ("unconditional", "Unconditional")])

    submitted_on = models.DateField(null=True, blank=True)
    offer_received_on = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True, db_index=True)

    visa_status = models.CharField(max_length=20, choices=STATUS_VISA, default="not_applied")
    visa_applied_on = models.DateField(null=True, blank=True)
    biometrics_on = models.DateField(null=True, blank=True)
    interview_on = models.DateField(null=True, blank=True)
    visa_decision_on = models.DateField(null=True, blank=True)
    visa_refusal_reason = models.TextField(blank=True)

    internal_notes = models.TextField(blank=True)     # SRS FR-APP-08 (never shown to student)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["stage", "assigned_officer"])]

    def save(self, *args, **kwargs):
        if not self.reference_no:
            year = timezone.now().year
            last = Application.all_objects.filter(reference_no__startswith=f"DSG-{year}-") \
                .order_by("-reference_no").values_list("reference_no", flat=True).first()
            seq = int(last.split("-")[-1]) + 1 if last else 1
            self.reference_no = f"DSG-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_no} — {self.student} → {self.university}"

    @property
    def progress_percent(self):
        try:
            idx = STAGE_ORDER.index(self.stage)
        except ValueError:
            idx = 0
        return int(round((idx + 1) / len(STAGE_ORDER) * 100))

    def timeline(self):
        """Returns each stage with done/current flags for the portal tracker."""
        try:
            idx = STAGE_ORDER.index(self.stage)
        except ValueError:
            idx = 0
        out = []
        for i, (value, label) in enumerate(Stage.choices):
            out.append({"value": value, "label": label,
                        "done": i < idx, "current": i == idx, "future": i > idx})
        return out

    @property
    def days_to_deadline(self):
        if not self.deadline:
            return None
        return (self.deadline - timezone.localdate()).days


class ApplicationStageHistory(models.Model):
    """SRS FR-APP-03 — immutable stage transition log."""
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="stage_history")
    from_stage = models.CharField(max_length=30, blank=True)
    to_stage = models.CharField(max_length=30)
    note = models.CharField(max_length=400, blank=True)
    actor = models.ForeignKey("accounts.User", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="stage_changes")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Application stage history"

    def __str__(self):
        return f"{self.application.reference_no}: {self.from_stage} → {self.to_stage}"


class Document(TimeStampedModel):
    """SRS FR-STU-05 / FR-APP-04 — student document with verification workflow."""
    STATUS = [("pending", "Pending review"), ("verified", "Verified"),
              ("rejected", "Rejected"), ("reupload", "Re-upload requested")]

    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE,
                                related_name="documents")
    application = models.ForeignKey(Application, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=180, blank=True)
    file = models.FileField(upload_to="documents/%Y/%m/")
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    remarks = models.CharField(max_length=400, blank=True)
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="reviewed_documents")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.student}"

    @property
    def filename(self):
        return self.file.name.rsplit("/", 1)[-1] if self.file else ""
