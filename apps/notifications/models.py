"""In-app notifications, messaging and email templates (SRS 6.x, FR-STU-09/12, FR-USR-05)."""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    LEVELS = [("info", "Info"), ("success", "Success"),
              ("warning", "Warning"), ("danger", "Action required")]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="notifications")
    title = models.CharField(max_length=180)
    body = models.CharField(max_length=400, blank=True)
    level = models.CharField(max_length=10, choices=LEVELS, default="info")
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient}: {self.title}"


class MessageThread(TimeStampedModel):
    """SRS FR-STU-09 — one thread per student."""
    student = models.OneToOneField("accounts.StudentProfile", on_delete=models.CASCADE,
                                   related_name="thread")
    subject = models.CharField(max_length=180, default="Counselling conversation")

    def __str__(self):
        return f"Thread — {self.student}"

    def unread_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(TimeStampedModel):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="sent_messages")
    body = models.TextField()
    attachment = models.FileField(upload_to="messages/", blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"


class EmailTemplate(TimeStampedModel):
    """SRS FR-USR-05 — editable templates with {{ placeholders }}."""
    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=140)
    subject = models.CharField(max_length=220)
    body = models.TextField(help_text="Django template syntax, e.g. {{ student_name }}")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def render(self, context):
        from django.template import Context, Template
        ctx = Context(context)
        return (Template(self.subject).render(ctx), Template(self.body).render(ctx))
