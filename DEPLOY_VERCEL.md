# Deploying Dream Spot Global to Vercel + Neon

Live in about 15 minutes, with all of your local data (users, leads, courses,
destinations, applications) carried across.

---

## Read this first — two real limitations

**1. Uploaded files do not survive.** Vercel's filesystem is read-only apart from
`/tmp`, which is wiped when the function goes cold. Student document uploads, the
logo and favicon uploaded through Site Settings, and blog images will appear to
work and then vanish within minutes. Everything already in the database is fine —
this only affects *new* file uploads. For a client demo this is usually
acceptable. Before real students use it, move media to object storage
(Vercel Blob, Cloudinary or Amazon S3).

**2. Scheduled jobs do not run.** `send_reminders`, `lead_housekeeping` and
`expire_scholarships` need a cron host. Use Vercel Cron (paid) or run them from
any machine against the same `DATABASE_URL`.

Everything else — the whole website, the dashboard, the portal, login, lead
capture, search, booking — works normally.

---

## Step 1 — Create the Neon database

1. https://console.neon.tech → **New project** → name it `dreamspot-global`.
   Pick the region closest to Dhaka (Singapore or US East both work).
2. On the project dashboard, copy the **connection string**. It looks like:

   ```
   postgresql://neondb_owner:npg_xxxx@ep-cool-fire-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

Keep it somewhere safe — you need it twice.

---

## Step 2 — Copy your local data into Neon

Run this from your project folder on your Mac:

```bash
cd ~/Downloads/dreamspot-global
source .venv/bin/activate
pip install "psycopg[binary]" whitenoise

# 2a. Export everything from the local SQLite database
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.permission \
  --exclude sessions --exclude admin.logentry \
  --indent 2 -o data.json

# 2b. Point at Neon, create the tables, then load the data
export DATABASE_URL="paste-your-neon-connection-string-here"
python manage.py migrate
python manage.py loaddata data.json
```

Verify it worked:

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.leads.models import Lead
print('users:', get_user_model().objects.count(), 'leads:', Lead.objects.count())"
```

Passwords are stored as hashes, so every existing login keeps working on the
live site. `data.json` is in `.gitignore` and `.vercelignore` — do not commit it.

---

## Step 3 — Push to GitHub

```bash
unset DATABASE_URL                      # back to local SQLite for development
python manage.py collectstatic --noinput
git add -A
git commit -m "Add Vercel deployment configuration"
git push
```

`collectstatic` matters: the `staticfiles/` folder is committed on purpose,
because WhiteNoise serves the CSS and JS straight out of the deployment.
Re-run it and commit again any time you change a stylesheet.

---

## Step 4 — Deploy on Vercel

1. https://vercel.com → **Add New → Project** → import `austroboy/dream_spot_global`.
2. Framework preset: **Other**. Leave the build and output settings empty.
3. Open **Environment Variables** and add these four:

   | Name | Value |
   |---|---|
   | `DJANGO_ENV` | `production` |
   | `SECRET_KEY` | a long random string (see below) |
   | `DATABASE_URL` | your Neon connection string |
   | `PYTHON_VERSION` | `3.12` |

   Generate the secret key with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

4. **Deploy.** First build takes two to three minutes.

Your site is live at `https://dream-spot-global.vercel.app` (or whatever name
Vercel assigns). Sign in at `/accounts/login/` with your existing accounts.

---

## Step 5 — After the first deploy

Add these environment variables once you know the final URL, then redeploy:

| Name | Value |
|---|---|
| `ALLOWED_HOSTS` | `dream-spot-global.vercel.app,dreamspotglobal.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://dream-spot-global.vercel.app,https://dreamspotglobal.com` |

For a custom domain: Vercel → Settings → Domains → add `dreamspotglobal.com`,
then point the DNS records Vercel shows you.

---

## Emails on the live site

`EMAIL_BACKEND` defaults to the console backend, so on Vercel emails are written
to the function logs instead of being sent. To send for real, add:

| Name | Value |
|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.sendgrid.net` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | `apikey` |
| `EMAIL_HOST_PASSWORD` | your SendGrid API key |
| `DEFAULT_FROM_EMAIL` | `Dream Spot Global <info@dreamspotglobal.com>` |

---

## Troubleshooting

**500 on every page** — `DATABASE_URL` is missing or wrong, or `SECRET_KEY` is
not set. Check Vercel → Deployments → the failing deployment → **Functions** logs.

**`DisallowedHost` error** — add your domain to `ALLOWED_HOSTS` and redeploy.

**Site loads but looks unstyled** — `staticfiles/` was not committed. Run
`python manage.py collectstatic --noinput`, commit and push.

**CSRF verification failed on login** — add your domain to
`CSRF_TRUSTED_ORIGINS` with the `https://` prefix.

**An uploaded logo disappeared** — expected, see the limitations at the top.

---

## Making changes later

```bash
git add -A && git commit -m "your message" && git push
```

Vercel redeploys automatically on every push to `main`. The database is separate,
so your data is untouched by deployments. If you change models, run the migration
against Neon before pushing:

```bash
DATABASE_URL="your-neon-url" python manage.py migrate
```
