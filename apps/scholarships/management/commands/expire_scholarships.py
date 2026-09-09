"""Deactivate scholarships whose deadline has passed (SRS FR-SCH-03)."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.scholarships.models import Scholarship


class Command(BaseCommand):
    help = "Mark scholarships with a past deadline as expired."

    def handle(self, *args, **options):
        expired = Scholarship.objects.filter(
            is_active=True, application_deadline__lt=timezone.localdate())
        count = expired.count()
        expired.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Expired {count} scholarship(s)."))
