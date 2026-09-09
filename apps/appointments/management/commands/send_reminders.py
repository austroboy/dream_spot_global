"""Send appointment reminders (SRS FR-APT-05). Run every 15 minutes from cron/Celery beat."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.appointments.services import due_reminders
from apps.notifications.services import notify_user, send_email


class Command(BaseCommand):
    help = "Send 24-hour and 2-hour appointment reminders."

    def handle(self, *args, **options):
        sent = 0
        for appt, kind in due_reminders():
            when = timezone.localtime(appt.start_datetime).strftime("%A %d %B, %I:%M %p")
            send_email(
                subject=f"Reminder: your counselling session {'tomorrow' if kind == '24h' else 'in 2 hours'}",
                to=appt.email,
                body=(f"Dear {appt.full_name},\n\nThis is a reminder of your free counselling "
                      f"session on {when} ({appt.get_mode_display()}).\n\n"
                      "House 21, Road 01, Sector 9, Uttara, Dhaka\n"
                      "+880 1410-157209\n\nDream Spot Global"))
            if appt.student:
                notify_user(appt.student.user, "Counselling session reminder",
                            body=when, level="info", url="/portal/appointments/")
            if kind == "24h":
                appt.reminder_24h_sent = True
            else:
                appt.reminder_2h_sent = True
            appt.save(update_fields=["reminder_24h_sent", "reminder_2h_sent"])
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} reminder(s)."))
