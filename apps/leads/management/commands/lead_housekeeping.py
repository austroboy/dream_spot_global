"""Nightly lead housekeeping (SRS FR-LDM-09, PRV-05).

- Notifies counsellors about leads with no activity for LEAD_OVERDUE_DAYS.
- Anonymises closed leads older than LEAD_DATA_RETENTION_YEARS.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.leads.models import Lead, OPEN_STATUSES
from apps.notifications.services import notify_user


class Command(BaseCommand):
    help = "Flag overdue leads and anonymise expired records."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=settings.LEAD_OVERDUE_DAYS)
        overdue = Lead.objects.filter(status__in=OPEN_STATUSES, last_activity_at__lt=cutoff)
        flagged = 0
        for lead in overdue.select_related("assigned_to__user"):
            if lead.assigned_to:
                notify_user(lead.assigned_to.user, f"Overdue follow-up: {lead.full_name}",
                            body=f"No activity since {lead.last_activity_at:%d %b %Y}.",
                            level="warning", url=f"/dashboard/leads/{lead.pk}/")
                flagged += 1

        retention = timezone.now() - timezone.timedelta(
            days=365 * settings.LEAD_DATA_RETENTION_YEARS)
        expired = Lead.objects.filter(created_at__lt=retention).exclude(
            status__in=OPEN_STATUSES)
        anonymised = 0
        for lead in expired:
            if lead.email.endswith("@anonymised.invalid"):
                continue
            lead.full_name = "Anonymised lead"
            lead.email = f"lead-{lead.pk}@anonymised.invalid"
            lead.phone = "+8800000000000"
            lead.message = ""
            lead.ip_address = None
            lead.save(update_fields=["full_name", "email", "phone", "message", "ip_address"])
            anonymised += 1

        self.stdout.write(self.style.SUCCESS(
            f"Flagged {flagged} overdue lead(s); anonymised {anonymised} expired record(s)."))
