# Dream Spot Global — Website & Admin Dashboard

A complete Django 5 (MVT) implementation of the Dream Spot Global SRS: a public
study-abroad website, a role-based staff dashboard and a student portal.

**Dream Spot Global** — Education • Career • Immigration
House 21, Road 01, Sector 9, Uttara, Dhaka, Bangladesh
+880 1410-157209 / +880 1612649451 · dreamspotglobal@gmail.com

---

## 1. Quick start (5 minutes)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # edit SECRET_KEY at minimum
python manage.py migrate
python manage.py seed_demo                             # real reference data + demo records
python manage.py runserver
```

Open http://127.0.0.1:8000

### Demo accounts (created by `seed_demo`)

| Role | Login | Password | Lands on |
|---|---|---|---|
| Administrator | `admin@dreamspotglobal.com` | `DreamSpot#2026` | `/dashboard/` |
| Counsellor | `counsellor@dreamspotglobal.com` | `DreamSpot#2026` | `/dashboard/` |
| Application Officer | `officer@dreamspotglobal.com` | `DreamSpot#2026` | `/dashboard/` |
| Content Editor | `editor@dreamspotglobal.com` | `DreamSpot#2026` | `/dashboard/` |
| Student | `student@example.com` | `DreamSpot#2026` | `/portal/` |

> Change every password before going live. `seed_demo --minimal` loads only the
> reference data (destinations, services, pages, email templates) and is safe to
> run on a production database.

---

## 2. What is included

### Public website
Homepage with 13 configurable sections · 8 destination guides (overview, intakes,
cost of living in BDT, visa checklist) · destination comparison · course search with
seven filters, sorting and pagination · university directory and profiles · course
comparison and shortlist · scholarships with deadline filtering · events with
registration and waitlist · blog with categories and tags · success stories · FAQ ·
free 4-step profile assessment with an eligibility engine · free counselling booking
with real slot availability and `.ics` invites · contact page · newsletter ·
search · legal pages · sitemap.xml, robots.txt and JSON-LD structured data.

### Staff dashboard (`/dashboard/`)
KPI overview with six charts and an "requires attention" panel · lead list with
filters, sorting, bulk actions and CSV export · drag-and-drop pipeline board ·
lead detail with notes, activity timeline, status changes, follow-up reminders and
one-click conversion to a student · student records · application tracker across
twelve stages with history and student notifications · document verification queue ·
appointment management and counsellor availability · generic CRUD for 22 content
types · staff users, permission matrix, site settings, audit log and reports.

### Student portal (`/portal/`)
Dashboard, profile with completeness meter, academic records, document upload with
a checklist and verification status, application tracker, appointments, shortlist,
messaging with the counsellor, notifications and a personal data export.

---

## 3. Role-based access control

Permissions live in `apps/accounts/permissions.py` as a single `CAPABILITIES` map
that mirrors SRS §12.2. Every dashboard view is guarded by `@require_capability`,
and querysets are additionally scoped so a counsellor only ever sees their own
leads and students.

| Capability | Admin | Counsellor | Officer | Editor |
|---|:--:|:--:|:--:|:--:|
| View all leads | ✓ | own only | – | – |
| Edit / convert leads | ✓ | ✓ | – | – |
| Reassign leads | ✓ | – | – | – |
| View students | ✓ | own | assigned | – |
| Edit applications | ✓ | ✓ | ✓ | – |
| Verify documents | ✓ | – | ✓ | – |
| Manage appointments | ✓ | ✓ | – | – |
| Publish content / catalogue | ✓ | – | – | ✓ |
| Manage users & settings | ✓ | – | – | – |
| Audit log | ✓ | – | – | – |

The live matrix is visible in the dashboard at **Administration → Roles & permissions**.

---

## 4. Project structure

```
config/               settings (base / development / production), urls, wsgi, asgi
apps/
  core/               site settings, homepage sections, pages, audit log, middleware
  accounts/           custom User, roles, staff & student profiles, RBAC, auth views
  destinations/       countries, intakes, cost of living, visa requirements
  institutions/       universities, courses, shortlist, faceted search
  services/           the nine consultancy services
  scholarships/       scholarships with deadline handling
  leads/              lead model, capture services, assessment engine, wizard
  applications/       applications, 12-stage pipeline, documents
  appointments/       availability, slots, booking, .ics, reminders
  blog/ events/ testimonials/ faqs/     content apps
  notifications/      in-app notifications, messaging, editable email templates
  dashboard/          staff dashboard views, forms and content CRUD registry
  portal/             student portal
templates/            base, includes, and one folder per app
static/css/brand.css  the full design system (tokens, components, responsive rules)
static/js/            progressive-enhancement JS, charts, kanban drag & drop
```

---

## 5. Design system

`static/css/brand.css` implements SRS §4 with CSS custom properties, so a rebrand
is a one-file change:

| Token | Value | Use |
|---|---|---|
| `--brand-navy` | `#123A73` | headings, primary surfaces |
| `--brand-navy-dark` | `#0C2751` | footer, gradients |
| `--brand-gold` | `#F2A526` | CTAs and accents only |
| `--ink` / `--muted` | `#14213D` / `#5B6B85` | body text |
| `--surface-alt` | `#F5F8FC` | alternating section bands |

Gold is reserved for calls to action and accents because it fails contrast at
small text sizes. Sections use a 96px vertical rhythm (56px on mobile), one radius
scale, and navy-tinted shadows rather than grey.

---

## 6. Scheduled jobs

Run these from cron, Celery beat or your host's scheduler:

```bash
*/15 * * * *  python manage.py send_reminders        # 24h and 2h appointment reminders
0 2 * * *     python manage.py lead_housekeeping     # overdue alerts + data retention
0 3 * * *     python manage.py expire_scholarships   # hide passed deadlines
```

---

## 7. Testing

```bash
python manage.py test                 # 61 tests
coverage run manage.py test && coverage report
```

Coverage includes the RBAC matrix (positive **and** negative cases per SRS QA-03),
lead deduplication, honeypot and phone validation, the assessment engine,
double-booking prevention, portal data isolation, upload restrictions,
slug-change redirects, audit logging and maintenance mode.

---

## 8. Deployment

### Docker

```bash
cp .env.example .env      # set SECRET_KEY, ALLOWED_HOSTS, POSTGRES_PASSWORD
docker compose up --build
```

### Manual (Ubuntu + Nginx + Gunicorn)

```bash
export DJANGO_ENV=production
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

Production settings enable HSTS, SSL redirect, secure cookies and hashed static
files automatically. Set `POSTGRES_DB` to switch from SQLite to PostgreSQL — no
code change needed.

---

## 9. Before you go live

1. **Set a real `SECRET_KEY`** and `DEBUG=False`.
2. **Move off the Gmail address for sending.** `dreamspotglobal@gmail.com` is fine
   as a contact address, but sending system mail from it will land in spam. Use a
   domain sender (`info@dreamspotglobal.com`) through SendGrid, Mailgun or SES and
   configure SPF, DKIM and DMARC.
3. **Add the missing social URLs.** Instagram and LinkedIn fields exist in Site
   Settings and stay hidden until filled.
4. **Upload the brand assets** (logo, favicon, hero and destination photography)
   under Site Settings and each destination record.
5. **Add the reCAPTCHA keys** in `.env` to switch on the second spam layer.
6. **Change every seeded password** and delete the demo student account.
7. **Set up backups** for the database and the `media/` directory.

---

## 10. Notes on third-party assets

The dashboard charts use Chart.js from a CDN when it is reachable and fall back to
a built-in dependency-free SVG renderer when it is not, so the dashboard works on
restricted networks and offline installs without any extra setup.
