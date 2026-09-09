"""Slot generation and double-booking protection (SRS FR-APT-03)."""
from datetime import time, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Role, StaffProfile, User
from apps.appointments.models import Appointment, Availability, BlackoutDate
from apps.appointments.services import available_slots
from apps.core.models import SiteSettings


class AppointmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        user = User.objects.create_user(username="c", email="c@dsg.com", password="pw",
                                        role=Role.COUNSELLOR)
        cls.counsellor = StaffProfile.objects.create(user=user)
        for weekday in range(7):
            Availability.objects.create(counsellor=cls.counsellor, weekday=weekday,
                                        start_time=time(10, 0), end_time=time(17, 0),
                                        slot_minutes=30)

    def test_slots_are_generated(self):
        calendar = available_slots(self.counsellor)
        self.assertTrue(calendar)
        self.assertTrue(all(len(v) > 0 for v in calendar.values()))

    def test_double_booking_is_impossible(self):
        slot = timezone.now() + timedelta(days=3)
        Appointment.objects.create(counsellor=self.counsellor, full_name="First",
                                   email="f@x.com", phone="+8801711111111",
                                   start_datetime=slot)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(counsellor=self.counsellor, full_name="Second",
                                           email="s@x.com", phone="+8801722222222",
                                           start_datetime=slot)

    def test_booked_slot_disappears_from_calendar(self):
        calendar = available_slots(self.counsellor)
        day = list(calendar)[0]
        chosen = calendar[day][0]
        from django.utils.dateparse import parse_datetime
        Appointment.objects.create(counsellor=self.counsellor, full_name="Taken",
                                   email="t@x.com", phone="+8801733333333",
                                   start_datetime=parse_datetime(chosen["iso"]))
        refreshed = available_slots(self.counsellor)
        self.assertNotIn(chosen["iso"], [s["iso"] for s in refreshed.get(day, [])])

    def test_blackout_date_removes_the_whole_day(self):
        calendar = available_slots(self.counsellor)
        day = list(calendar)[0]
        BlackoutDate.objects.create(counsellor=self.counsellor, date=day, reason="Holiday")
        self.assertNotIn(day, available_slots(self.counsellor))

    def test_ics_contains_calendar_envelope(self):
        appt = Appointment.objects.create(counsellor=self.counsellor, full_name="ICS",
                                          email="i@x.com", phone="+8801744444444",
                                          start_datetime=timezone.now() + timedelta(days=2))
        ics = appt.ics()
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("END:VEVENT", ics)
