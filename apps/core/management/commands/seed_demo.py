"""Populate the database with Dream Spot Global's real reference data + demo records.

    python manage.py seed_demo            # reference data + demo content
    python manage.py seed_demo --minimal  # reference data only (safe for production)
"""
import random
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Role, StaffProfile, StudentProfile
from apps.appointments.models import Availability
from apps.applications.models import Application, ApplicationStageHistory, Stage
from apps.blog.models import BlogPost, Category
from apps.core.models import (HeroSlide, HomepageSection, JourneyStep, Page, SiteSettings,
                              TeamMember, WhyUsPoint)
from apps.destinations.models import CostOfLiving, Country, Intake, VisaRequirement
from apps.events.models import Event
from apps.faqs.models import FAQ, FAQCategory
from apps.institutions.models import Course, University
from apps.leads.models import Lead, LeadActivity, LeadStatus
from apps.notifications.models import EmailTemplate
from apps.scholarships.models import Scholarship
from apps.services.models import Service, ServiceStep
from apps.testimonials.models import Testimonial

User = get_user_model()

COUNTRIES = [
    {"name": "United Kingdom", "code": "GB", "currency": "GBP", "tuition": (12000, 30000),
     "living": (800, 1400), "rate": 145, "visa": "Student Route (Tier 4)",
     "psw": "Graduate Route — 2 years (3 for PhD)", "work": "20 hours per week in term time",
     "tagline": "Two-year Graduate Route and one-year master's degrees."},
    {"name": "Australia", "code": "AU", "currency": "AUD", "tuition": (20000, 45000),
     "living": (1400, 2200), "rate": 78, "visa": "Subclass 500",
     "psw": "Temporary Graduate visa — 2 to 4 years",
     "work": "48 hours per fortnight", "tagline": "Strong post-study work rights and high wages."},
    {"name": "Canada", "code": "CA", "currency": "CAD", "tuition": (15000, 35000),
     "living": (1000, 1800), "rate": 88, "visa": "Study Permit",
     "psw": "PGWP — up to 3 years", "work": "24 hours per week off campus",
     "tagline": "Clear route from study permit to permanent residence."},
    {"name": "USA", "code": "US", "currency": "USD", "tuition": (20000, 55000),
     "living": (1200, 2200), "rate": 120, "visa": "F-1 Student Visa",
     "psw": "OPT — 12 months (36 for STEM)", "work": "20 hours per week on campus",
     "tagline": "The widest choice of universities and research funding in the world."},
    {"name": "Germany", "code": "DE", "currency": "EUR", "tuition": (0, 20000),
     "living": (850, 1200), "rate": 130, "visa": "National Visa (Type D)",
     "psw": "18-month job seeker visa", "work": "120 full or 240 half days per year",
     "tagline": "Public universities with little or no tuition fee."},
    {"name": "Finland", "code": "FI", "currency": "EUR", "tuition": (6000, 18000),
     "living": (700, 1100), "rate": 130, "visa": "Residence Permit for Studies",
     "psw": "2-year post-study residence permit", "work": "30 hours per week average",
     "tagline": "Scholarship-rich programmes taught entirely in English."},
    {"name": "Ireland", "code": "IE", "currency": "EUR", "tuition": (10000, 25000),
     "living": (900, 1500), "rate": 130, "visa": "Stamp 2 Student Permission",
     "psw": "Third Level Graduate Scheme — up to 2 years",
     "work": "20 hours per week in term time",
     "tagline": "English-speaking EU hub for tech and pharma careers."},
    {"name": "New Zealand", "code": "NZ", "currency": "NZD", "tuition": (18000, 35000),
     "living": (1100, 1700), "rate": 72, "visa": "Fee Paying Student Visa",
     "psw": "Post Study Work Visa — up to 3 years", "work": "20 hours per week",
     "tagline": "Safe, welcoming and strong in agriculture, IT and engineering."},
]

SERVICES = [
    ("Free Counselling", "compass", "A no-obligation one-to-one session to map your goals, "
     "budget and destination."),
    ("Profile Assessment", "clipboard-check", "We assess your academics, English score and "
     "finances against real admission criteria."),
    ("Course Selection", "book-open", "A shortlist of courses that match your background, "
     "career plan and budget."),
    ("University Selection", "building", "Realistic university choices — ambitious, balanced "
     "and safe options together."),
    ("Application Processing", "file-text", "We prepare, check and submit every application "
     "and chase the decision for you."),
    ("Scholarship Guidance", "award", "We identify the scholarships you actually qualify for "
     "and help you apply on time."),
    ("SOP & LOR Guidance", "pen-tool", "Structured help writing a Statement of Purpose and "
     "securing strong recommendation letters."),
    ("Visa Guidance", "stamp", "Document checklists, financial preparation, form filing and "
     "interview coaching."),
    ("Pre-departure Support", "plane", "Accommodation, airport pickup, banking, packing and "
     "what to expect in week one."),
]

JOURNEY = [
    ("Free counselling", "Tell us your goals, grades and budget in a relaxed session."),
    ("Profile assessment", "We check your eligibility against real entry requirements."),
    ("University shortlist", "You receive a shortlist with costs, deadlines and outcomes."),
    ("Application & offer", "We prepare documents, submit and follow up until the offer arrives."),
    ("Visa filing", "Financial documents, forms, biometrics and interview preparation."),
    ("Pre-departure", "Accommodation, tickets, banking and a full briefing before you fly."),
]

WHY_US = [
    ("Certified counsellors", "Our advisers are trained on each destination's admission and "
     "visa system — not generalists reading a brochure."),
    ("Honest shortlists", "We recommend universities that fit your profile and budget, not "
     "whichever pays the highest commission."),
    ("End-to-end handling", "One team from first enquiry to airport departure, so nothing "
     "falls between the gaps."),
    ("Strong visa record", "Meticulous documentation and interview preparation behind a very "
     "high approval rate."),
    ("Scholarship focus", "We actively hunt funding — many of our students study on partial "
     "or full scholarships."),
    ("After you land", "Accommodation, banking and settling-in help continue after you arrive."),
]

FAQS = [
    ("General", "Is the counselling really free?",
     "Yes. Counselling, profile assessment, university shortlisting and application guidance "
     "are free of charge. You pay only the university and government fees."),
    ("General", "How early should I start?",
     "Start 9 to 12 months before your intended intake. That leaves time for English tests, "
     "documents, scholarships and visa processing."),
    ("Admission", "What are the minimum academic requirements?",
     "It varies by country and level. For a master's degree most universities look for a "
     "bachelor's with a CGPA of 2.5 or above out of 4, but many accept lower with relevant "
     "work experience."),
    ("English", "Can I apply without IELTS?",
     "In several cases yes — many universities in the UK, Ireland and Canada accept a Medium "
     "of Instruction certificate or their own internal English test."),
    ("Finance", "How much bank balance do I need to show?",
     "It depends on the destination and course length. We calculate the exact figure for your "
     "case and tell you how long the funds must be held."),
    ("Visa", "What if I have a previous visa refusal?",
     "A refusal is not the end. We prepare a detailed explanation letter addressing the exact "
     "refusal ground and strengthen the weak areas of your file."),
]

TEMPLATES = [
    ("lead_confirmation", "Lead confirmation", "We have received your enquiry",
     "Dear {{ lead.full_name }},\n\nThank you for contacting Dream Spot Global."),
    ("appointment_confirmation", "Appointment confirmation", "Your counselling session is confirmed",
     "Dear {{ name }},\n\nYour session is confirmed for {{ when }}."),
    ("appointment_reminder", "Appointment reminder", "Reminder: your session is tomorrow",
     "Dear {{ name }},\n\nThis is a reminder for your session on {{ when }}."),
    ("document_verified", "Document verified", "Your document has been verified",
     "Dear {{ name }},\n\nYour {{ document }} has been verified."),
    ("document_rejected", "Document rejected", "Action needed on your document",
     "Dear {{ name }},\n\nYour {{ document }} needs attention: {{ remarks }}."),
    ("application_update", "Application stage update", "Update on application {{ reference }}",
     "Dear {{ name }},\n\nYour application has moved to {{ stage }}."),
    ("student_welcome", "Student portal welcome", "Welcome to your student portal",
     "Dear {{ name }},\n\nYour portal account is ready. Login: {{ email }}."),
    ("event_registration", "Event registration", "You are registered for {{ event }}",
     "Dear {{ name }},\n\nYour place at {{ event }} is confirmed."),
]


class Command(BaseCommand):
    help = "Seed reference data and (optionally) demo content for Dream Spot Global."

    def add_arguments(self, parser):
        parser.add_argument("--minimal", action="store_true",
                            help="Reference data only, no demo leads/students.")

    def handle(self, *args, **options):
        minimal = options["minimal"]
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Dream Spot Global…"))

        self._site_settings()
        countries = self._countries()
        self._services()
        self._homepage()
        self._pages()
        self._faqs()
        self._email_templates()
        users = self._users()
        unis, courses = self._universities(countries)
        self._scholarships(countries, unis)
        self._blog(users)
        self._events(countries, unis)
        self._availability(users)

        if not minimal:
            self._testimonials(countries)
            self._leads(countries, users)
            self._students(countries, users, courses)

        self.stdout.write(self.style.SUCCESS(
            "\nDone. Sign in at /accounts/login/ with:\n"
            "  admin@dreamspotglobal.com      / DreamSpot#2026 (Administrator)\n"
            "  counsellor@dreamspotglobal.com / DreamSpot#2026 (Counsellor)\n"
            "  officer@dreamspotglobal.com    / DreamSpot#2026 (Application Officer)\n"
            "  editor@dreamspotglobal.com     / DreamSpot#2026 (Content Editor)\n"
            "  student@example.com            / DreamSpot#2026 (Student portal)\n"))

    # ------------------------------------------------------------------ data
    def _site_settings(self):
        s = SiteSettings.load()
        s.company_name = "Dream Spot Global"
        s.tagline = "Education • Career • Immigration"
        s.about_short = ("Dream Spot Global is a study abroad education consultancy based in "
                         "Uttara, Dhaka. We guide Bangladeshi students from the first "
                         "counselling session to departure day.")
        s.address = "House 21, Road 01, Sector 9, Uttara, Dhaka, Bangladesh"
        s.phone_primary = "+880 1410-157209"
        s.phone_secondary = "+880 1612649451"
        s.email = "dreamspotglobal@gmail.com"
        s.whatsapp = "8801410157209"
        s.office_hours = "Saturday – Thursday, 10:00 AM – 7:00 PM"
        s.facebook = "https://www.facebook.com/dreamspotglobalpage"
        s.default_meta_title = "Dream Spot Global — Study Abroad Consultancy in Dhaka"
        s.default_meta_description = (
            "Free counselling, university admission and student visa guidance for the UK, "
            "Australia, Canada, USA, Germany, Finland, Ireland and New Zealand.")
        s.save()
        self.stdout.write("  • Site settings")

    def _countries(self):
        objs = {}
        for order, data in enumerate(COUNTRIES):
            c, _ = Country.objects.get_or_create(name=data["name"], defaults={
                "code": data["code"], "currency": data["currency"]})
            c.currency = data["currency"]
            c.code = data["code"]
            c.tagline = data["tagline"]
            c.tuition_min, c.tuition_max = data["tuition"]
            c.living_cost_min, c.living_cost_max = data["living"]
            c.visa_duration = data["visa"]
            c.post_study_work = data["psw"]
            c.work_hours_allowed = data["work"]
            c.display_order = order
            c.is_active = True
            c.is_featured = True
            c.overview = (f"{data['name']} is one of the most popular destinations for "
                          "Bangladeshi students, offering internationally recognised degrees, "
                          "a clear student visa route and the right to work during and after "
                          "study.")
            c.why_study = (f"Globally ranked universities\nEnglish-taught programmes\n"
                           f"{data['psw']}\nPart-time work: {data['work']}")
            c.admission_requirements = (
                "Academic transcripts and certificates\nEnglish proficiency evidence\n"
                "Passport valid for the duration of study\nStatement of Purpose\n"
                "Financial documents showing tuition and living costs")
            c.english_requirements = ("IELTS 6.0 overall for undergraduate and 6.5 for "
                                      "postgraduate is typical; PTE, TOEFL and Duolingo are "
                                      "widely accepted.")
            c.visa_process = (f"Apply for the {data['visa']} once you accept an offer and pay "
                              "the required deposit. Prepare financial evidence, book "
                              "biometrics and attend an interview if requested.")
            c.part_time_work = f"Students may work {data['work']}."
            c.save()

            cost, _ = CostOfLiving.objects.get_or_create(country=c)
            lo, hi = data["living"]
            cost.accommodation_min, cost.accommodation_max = int(lo * .45), int(hi * .45)
            cost.food_min, cost.food_max = int(lo * .22), int(hi * .22)
            cost.transport_min, cost.transport_max = int(lo * .12), int(hi * .12)
            cost.utilities_min, cost.utilities_max = int(lo * .11), int(hi * .11)
            cost.misc_min, cost.misc_max = int(lo * .10), int(hi * .10)
            cost.bdt_rate = Decimal(str(data["rate"]))
            cost.save()

            for name, months, offset in [("January / Spring", "January – February", 120),
                                         ("May / Summer", "May – June", 240),
                                         ("September / Fall", "September – October", 30)]:
                Intake.objects.get_or_create(country=c, name=name, defaults={
                    "months": months,
                    "application_deadline": timezone.localdate() + timedelta(days=offset)})

            for i, (title, desc) in enumerate([
                ("Valid passport", "Must be valid for the full duration of your course."),
                ("Offer letter / CAS", "Issued after you accept the offer and pay the deposit."),
                ("Financial evidence", "Bank statements or a loan sanction letter covering "
                                       "tuition and living costs."),
                ("English test result", "IELTS, PTE, TOEFL or an accepted alternative."),
                ("Academic documents", "All transcripts and certificates, attested where required."),
                ("Medical / TB certificate", "Required by several destinations from Bangladesh."),
            ]):
                VisaRequirement.objects.get_or_create(country=c, title=title, defaults={
                    "description": desc, "display_order": i})
            objs[c.name] = c
        self.stdout.write(f"  • {len(objs)} destinations with intakes, costs and visa checklists")
        return objs

    def _services(self):
        for order, (name, icon, desc) in enumerate(SERVICES):
            s, _ = Service.objects.get_or_create(name=name, defaults={"icon": icon})
            s.icon = icon
            s.short_description = desc
            s.description = desc + (" Our counsellors work through this with you step by step, "
                                    "and nothing is charged to the student.")
            s.whats_included = ("One-to-one session with a certified counsellor\n"
                                "Written summary you can keep\n"
                                "Follow-up support by phone, email or WhatsApp\n"
                                "No fee at any stage")
            s.display_order = order
            s.is_active = True
            s.is_featured = True
            s.save()
            for i, (t, d) in enumerate([
                ("Share your details", "Tell us your academic background and goals."),
                ("We review", "A counsellor studies your profile against real criteria."),
                ("You receive a plan", "Clear next steps, timelines and costs.")], start=1):
                ServiceStep.objects.get_or_create(service=s, number=i,
                                                  defaults={"title": t, "description": d})
        self.stdout.write(f"  • {len(SERVICES)} services")

    def _homepage(self):
        for order, (key, label) in enumerate(HomepageSection.KEYS):
            HomepageSection.objects.get_or_create(key=key, defaults={
                "heading": label, "display_order": order, "is_active": True})
        HeroSlide.objects.get_or_create(heading="Your dream university abroad starts here",
            defaults={
                "subheading": ("Free counselling, honest advice and end-to-end application "
                               "support for Bangladeshi students."),
                "cta_text": "Book Free Counselling", "cta_url": "/book-counselling/",
                "cta2_text": "Explore Destinations", "cta2_url": "/study-abroad/"})
        for i, (title, desc) in enumerate(JOURNEY, start=1):
            JourneyStep.objects.get_or_create(number=i, defaults={
                "title": title, "description": desc})
        for i, (title, desc) in enumerate(WHY_US):
            WhyUsPoint.objects.get_or_create(title=title, defaults={
                "description": desc, "display_order": i})
        self.stdout.write("  • Homepage sections, hero, journey and why-us points")

    def _pages(self):
        pages = [
            ("Privacy Policy", "privacy-policy",
             "This policy explains what personal data Dream Spot Global collects, why we "
             "collect it, how long we keep it and how you can ask us to delete it. We collect "
             "only the information needed to advise you on studying abroad and to submit "
             "applications on your behalf. We never sell your data."),
            ("Terms of Use", "terms",
             "By using this website you agree to provide accurate information and to use the "
             "site lawfully. Counselling outcomes, admission decisions and visa decisions are "
             "made by universities and government authorities, not by Dream Spot Global."),
            ("Disclaimer", "disclaimer",
             "Tuition fees, living costs, intakes and visa rules change frequently. All figures "
             "on this website are indicative and must be confirmed with the university or the "
             "relevant high commission before you make a financial commitment."),
            ("Refund Policy", "refund-policy",
             "Counselling and application guidance are provided free of charge. Third-party "
             "fees such as application fees, English test fees and visa fees are paid directly "
             "to those organisations and are governed by their own refund rules."),
        ]
        for title, slug, body in pages:
            Page.objects.get_or_create(slug=slug, defaults={
                "title": title, "body": body, "status": "published",
                "published_at": timezone.now(), "show_in_footer": True})
        self.stdout.write("  • Legal pages")

    def _faqs(self):
        for i, (cat_name, q, a) in enumerate(FAQS):
            cat, _ = FAQCategory.objects.get_or_create(name=cat_name)
            FAQ.objects.get_or_create(question=q, defaults={
                "answer": a, "category": cat, "display_order": i,
                "show_on_homepage": i < 5})
        self.stdout.write(f"  • {len(FAQS)} FAQs")

    def _email_templates(self):
        for key, name, subject, body in TEMPLATES:
            EmailTemplate.objects.get_or_create(key=key, defaults={
                "name": name, "subject": subject, "body": body})
        self.stdout.write(f"  • {len(TEMPLATES)} email templates")

    def _users(self):
        password = "DreamSpot#2026"
        made = {}
        spec = [
            ("admin", "admin@dreamspotglobal.com", "Rafiqul", "Islam", Role.ADMIN,
             "Managing Director"),
            ("counsellor", "counsellor@dreamspotglobal.com", "Nusrat", "Jahan",
             Role.COUNSELLOR, "Senior Education Counsellor"),
            ("counsellor2", "counsellor2@dreamspotglobal.com", "Tanvir", "Ahmed",
             Role.COUNSELLOR, "Education Counsellor"),
            ("officer", "officer@dreamspotglobal.com", "Sadia", "Rahman", Role.OFFICER,
             "Application Officer"),
            ("editor", "editor@dreamspotglobal.com", "Mahin", "Chowdhury", Role.EDITOR,
             "Content Editor"),
        ]
        for username, email, first, last, role, designation in spec:
            user, created = User.objects.get_or_create(username=username, defaults={
                "email": email, "first_name": first, "last_name": last, "role": role,
                "email_verified": True, "phone": "+8801710000000"})
            if created:
                user.set_password(password)
            user.role = role
            user.is_staff = role == Role.ADMIN
            user.is_superuser = role == Role.ADMIN
            user.save()
            profile, _ = StaffProfile.objects.get_or_create(user=user, defaults={
                "designation": designation})
            profile.designation = designation
            profile.show_on_website = role in (Role.ADMIN, Role.COUNSELLOR)
            profile.save()
            made[username] = profile
            if profile.show_on_website:
                TeamMember.objects.get_or_create(name=f"{first} {last}", defaults={
                    "designation": designation, "display_order": len(made)})
        self.stdout.write(f"  • {len(made)} staff users (password: {password})")
        return made

    def _universities(self, countries):
        catalogue = {
            "United Kingdom": [("University of Manchester", "Manchester", 32),
                               ("University of Leeds", "Leeds", 75),
                               ("Coventry University", "Coventry", 571)],
            "Australia": [("University of Melbourne", "Melbourne", 13),
                          ("Monash University", "Melbourne", 37),
                          ("Deakin University", "Geelong", 233)],
            "Canada": [("University of Toronto", "Toronto", 21),
                       ("University of Alberta", "Edmonton", 96),
                       ("Conestoga College", "Kitchener", None)],
            "USA": [("Arizona State University", "Tempe", 179),
                    ("Purdue University", "West Lafayette", 89)],
            "Germany": [("Technical University of Munich", "Munich", 28),
                        ("RWTH Aachen University", "Aachen", 106)],
            "Finland": [("University of Helsinki", "Helsinki", 115),
                        ("Aalto University", "Espoo", 109)],
            "Ireland": [("University College Dublin", "Dublin", 126),
                        ("Trinity College Dublin", "Dublin", 87)],
            "New Zealand": [("University of Auckland", "Auckland", 65),
                            ("Massey University", "Palmerston North", 239)],
        }
        programmes = [
            ("MSc Data Science", "master", "it", 12),
            ("MSc International Business Management", "master", "business", 12),
            ("MSc Civil Engineering", "master", "engineering", 18),
            ("BSc Computer Science", "bachelor", "it", 36),
            ("BBA Business Administration", "bachelor", "business", 36),
            ("MSc Public Health", "master", "health", 12),
        ]
        unis, courses = [], []
        for country_name, rows in catalogue.items():
            country = countries[country_name]
            for name, city, ranking in rows:
                u, _ = University.objects.get_or_create(name=name, defaults={
                    "country": country, "city": city, "world_ranking": ranking})
                u.country = country
                u.city = city
                u.world_ranking = ranking
                u.is_partner = True
                u.is_featured = ranking is not None and ranking < 120
                u.tuition_min, u.tuition_max = country.tuition_min, country.tuition_max
                u.description = (f"{name} is located in {city}, {country_name}. It welcomes "
                                 "international students from Bangladesh every intake and "
                                 "offers scholarships for strong academic profiles.")
                u.facilities = "Central library\nCareers service\nStudent accommodation\n" \
                               "Sports centre\nInternational student support"
                u.save()
                unis.append(u)
                for title, level, discipline, months in random.sample(programmes, 4):
                    fee = random.randint(country.tuition_min or 5000,
                                         country.tuition_max or 30000)
                    c, _ = Course.objects.get_or_create(title=title, university=u, defaults={
                        "study_level": level, "discipline": discipline,
                        "duration_months": months, "tuition_fee": fee,
                        "currency": country.currency})
                    c.overview = (f"The {title} at {name} prepares graduates for a global "
                                  "career with a mix of taught modules, project work and "
                                  "industry placement opportunities.")
                    c.entry_requirements = ("A recognised bachelor's degree with a good CGPA, "
                                            "or equivalent professional experience.")
                    c.english_requirements = "IELTS 6.5 overall with no band below 6.0."
                    c.career_outcomes = ("Graduates work in consultancy, industry and research "
                                         "roles across the region.")
                    c.scholarship_available = random.choice([True, False])
                    c.is_featured = random.choice([True, False])
                    c.save()
                    c.intakes.set(country.intakes.all()[:2])
                    courses.append(c)
        self.stdout.write(f"  • {len(unis)} universities and {len(courses)} courses")
        return unis, courses

    def _scholarships(self, countries, unis):
        rows = [
            ("Chevening Scholarship", "United Kingdom", "full",
             "Full tuition, stipend and airfare", "UK Government"),
            ("GREAT Scholarship for Bangladesh", "United Kingdom", "partial",
             "GBP 10,000 towards tuition", "British Council"),
            ("Australia Awards Scholarship", "Australia", "full",
             "Full tuition and living allowance", "Australian Government"),
            ("Melbourne International Undergraduate Scholarship", "Australia", "tuition_waiver",
             "Up to 100% tuition", "University of Melbourne"),
            ("Vanier Canada Graduate Scholarship", "Canada", "stipend",
             "CAD 50,000 per year", "Government of Canada"),
            ("Fulbright Foreign Student Program", "USA", "full",
             "Tuition, stipend and health cover", "US Department of State"),
            ("DAAD Study Scholarship", "Germany", "stipend",
             "EUR 934 per month", "DAAD"),
            ("Finland Scholarship", "Finland", "partial",
             "100% first-year tuition plus EUR 5,000", "Finnish universities"),
            ("Government of Ireland International Scholarship", "Ireland", "stipend",
             "EUR 10,000 stipend and fee waiver", "Higher Education Authority"),
            ("New Zealand Excellence Award", "New Zealand", "partial",
             "NZD 5,000 – 10,000", "Education New Zealand"),
        ]
        for i, (title, country_name, award, amount, provider) in enumerate(rows):
            country = countries[country_name]
            Scholarship.objects.get_or_create(title=title, defaults={
                "country": country, "provider": provider, "award_type": award,
                "award_amount": amount, "study_level": "Master's",
                "application_deadline": timezone.localdate() + timedelta(days=30 + i * 21),
                "eligibility": ("Open to Bangladeshi nationals with a strong academic record "
                                "and an offer from an eligible university."),
                "required_documents": "Academic transcripts\nEnglish test result\n"
                                      "Statement of Purpose\nTwo reference letters\nPassport",
                "description": f"{title} is offered by {provider} and covers {amount.lower()}.",
                "is_featured": i < 4})
        self.stdout.write(f"  • {len(rows)} scholarships")

    def _blog(self, users):
        author = users.get("editor")
        cats = ["Visa Updates", "Country Guides", "Scholarships", "IELTS & English",
                "Student Life"]
        for name in cats:
            Category.objects.get_or_create(name=name)
        posts = [
            ("UK Graduate Route explained for Bangladeshi students", "Visa Updates"),
            ("How much bank balance do you need for a Canadian study permit?", "Visa Updates"),
            ("Studying in Germany with little or no tuition fee", "Country Guides"),
            ("Ten scholarships Bangladeshi students actually win", "Scholarships"),
            ("IELTS 7.0 in eight weeks: a realistic study plan", "IELTS & English"),
            ("What your first month in Australia really costs", "Student Life"),
        ]
        for title, cat_name in posts:
            cat = Category.objects.get(name=cat_name)
            BlogPost.objects.get_or_create(title=title, defaults={
                "category": cat,
                "author": author.user if author else None,
                "status": "published", "published_at": timezone.now(),
                "excerpt": f"A practical guide for Bangladeshi students: {title.lower()}.",
                "body": (f"{title}\n\nThis guide walks through the requirements step by step, "
                         "with the figures and deadlines that apply to applicants from "
                         "Bangladesh.\n\nEvery number here should be confirmed with the "
                         "university or high commission before you commit money, because "
                         "rules change between intakes. Our counsellors keep an updated "
                         "checklist for each destination and will walk you through yours in "
                         "a free session.")})
        self.stdout.write(f"  • {len(posts)} blog posts")

    def _events(self, countries, unis):
        rows = [
            ("UK & Ireland Education Fair 2026", "fair", 14, False),
            ("Australia Study Webinar: September Intake", "webinar", 21, True),
            ("Canada Student Visa Seminar", "seminar", 35, False),
        ]
        for title, etype, days, online in rows:
            e, _ = Event.objects.get_or_create(title=title, defaults={
                "event_type": etype, "is_online": online, "status": "published",
                "start_datetime": timezone.now() + timedelta(days=days),
                "end_datetime": timezone.now() + timedelta(days=days, hours=4),
                "venue": "" if online else "Dream Spot Global, House 21, Road 01, Sector 9, "
                                           "Uttara, Dhaka",
                "online_link": "https://meet.google.com/dsg-event" if online else "",
                "capacity": 120,
                "description": (f"Join {title} to meet university representatives, get your "
                                "profile assessed on the spot and have your application fee "
                                "waived for participating universities.")})
            e.universities.set(unis[:4])
            e.countries.set(list(countries.values())[:3])
        self.stdout.write(f"  • {len(rows)} events")

    def _availability(self, users):
        for key in ("counsellor", "counsellor2"):
            profile = users.get(key)
            if not profile:
                continue
            for weekday in [5, 6, 0, 1, 2, 3]:      # Saturday to Thursday
                Availability.objects.get_or_create(
                    counsellor=profile, weekday=weekday,
                    start_time=time(10, 0), end_time=time(18, 0),
                    defaults={"slot_minutes": 30})
        self.stdout.write("  • Counsellor availability (Sat–Thu, 10:00–18:00)")

    def _testimonials(self, countries):
        rows = [
            ("Mahmudul Hasan", "University of Manchester", "MSc Data Science",
             "United Kingdom", "They built a shortlist that actually matched my CGPA, and my "
             "CAS came through in three weeks."),
            ("Farzana Akter", "Monash University", "Master of Public Health", "Australia",
             "The visa file was prepared so carefully that my Subclass 500 was granted in "
             "eleven days."),
            ("Rakib Hossain", "University of Toronto", "MEng Civil Engineering", "Canada",
             "I had a previous refusal. Dream Spot Global rewrote my explanation letter and "
             "the second application was approved."),
            ("Sumaiya Islam", "Technical University of Munich", "MSc Informatics", "Germany",
             "Almost no tuition fee and a blocked account set up correctly the first time."),
            ("Nafis Ahmed", "University College Dublin", "MSc Finance", "Ireland",
             "Honest advice about which universities were realistic for my profile."),
            ("Tasnim Zaman", "University of Auckland", "MSc Environmental Science",
             "New Zealand", "They found me a partial scholarship I did not know existed."),
        ]
        for name, uni, course, country_name, quote in rows:
            Testimonial.objects.get_or_create(student_name=name, defaults={
                "university": uni, "course": course,
                "country": countries.get(country_name),
                "quote": quote, "rating": 5, "is_approved": True, "is_featured": True,
                "intake_year": timezone.now().year})
        self.stdout.write(f"  • {len(rows)} testimonials")

    def _leads(self, countries, users):
        names = ["Ariful Islam", "Sabrina Sultana", "Imran Kabir", "Nusaiba Rahman",
                 "Jubayer Hossain", "Mim Akter", "Shakib Al Hasan", "Tania Ferdous",
                 "Rezaul Karim", "Anika Tabassum", "Fahim Shahriar", "Lamia Chowdhury",
                 "Mehedi Hasan", "Sadia Afrin", "Rifat Ahmed", "Nishat Tasnim",
                 "Tanjim Alam", "Sanjida Haque", "Asif Mahmud", "Rumana Parvin"]
        sources = ["homepage_cta", "contact", "destination_page", "assessment",
                   "appointment", "event", "facebook", "course_page"]
        statuses = [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED,
                    LeadStatus.SCHEDULED, LeadStatus.CONVERTED, LeadStatus.NOT_INTERESTED,
                    LeadStatus.LOST]
        counsellors = [p for k, p in users.items() if k.startswith("counsellor")]
        created = 0
        for i, name in enumerate(names):
            email = name.lower().replace(" ", ".") + "@example.com"
            if Lead.objects.filter(email=email).exists():
                continue
            lead = Lead.objects.create(
                full_name=name, email=email,
                phone=f"+88017{random.randint(10000000, 99999999)}",
                study_level=random.choice(["bachelor", "master"]),
                intended_intake=random.choice(["jan", "may", "sep"]),
                last_qualification=random.choice(["HSC", "BSc in CSE", "BBA", "BSc in EEE"]),
                gpa=Decimal(str(round(random.uniform(2.8, 4.0), 2))),
                english_test=random.choice(["ielts", "none", "pte"]),
                english_score=Decimal(str(random.choice([6.0, 6.5, 7.0]))),
                source=random.choice(sources),
                status=random.choice(statuses),
                assigned_to=random.choice(counsellors) if counsellors else None,
                message="I would like to know about scholarships and the visa process.",
                created_at=timezone.now() - timedelta(days=random.randint(0, 60)))
            lead.destinations.set(random.sample(list(countries.values()),
                                                random.randint(1, 3)))
            LeadActivity.objects.create(lead=lead, activity_type="created",
                                        summary="Lead created from the website")
            created += 1
        self.stdout.write(f"  • {created} demo leads")

    def _students(self, countries, users, courses):
        password = "DreamSpot#2026"
        student, created = User.objects.get_or_create(username="student", defaults={
            "email": "student@example.com", "first_name": "Ayesha", "last_name": "Siddiqua",
            "role": Role.STUDENT, "email_verified": True, "phone": "+8801712345678"})
        if created:
            student.set_password(password)
            student.save()
        profile, _ = StudentProfile.objects.get_or_create(user=student, defaults={
            "current_education": "BSc in Computer Science and Engineering",
            "institution_name": "North South University",
            "gpa": Decimal("3.65"), "year_of_passing": 2025,
            "english_test": "ielts", "english_score": Decimal("7.0"),
            "preferred_intake": "September / Fall", "preferred_level": "Master's",
            "city": "Dhaka", "nationality": "Bangladeshi",
            "assigned_counsellor": users.get("counsellor")})
        profile.preferred_destinations.set([countries["United Kingdom"], countries["Canada"]])

        if courses and not profile.applications.exists():
            course = random.choice([c for c in courses
                                    if c.university.country.name == "United Kingdom"] or courses)
            app = Application.objects.create(
                student=profile, university=course.university, course=course,
                intake="September / Fall", study_level=course.study_level,
                stage=Stage.OFFER_RECEIVED, assigned_officer=users.get("officer"),
                deadline=timezone.localdate() + timedelta(days=45),
                offer_type="conditional", currency=course.currency)
            for stage in [Stage.ENQUIRY, Stage.COUNSELLING, Stage.DOCUMENTS,
                          Stage.UNIVERSITY_APPLICATION, Stage.OFFER_RECEIVED]:
                ApplicationStageHistory.objects.create(
                    application=app, from_stage="", to_stage=stage,
                    note="Seeded demo history")
        self.stdout.write(f"  • Demo student portal account (student@example.com / {password})")
