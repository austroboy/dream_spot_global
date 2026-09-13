# Deploying Dream Spot Global to cPanel (HostSeba)

Target: `dreamspotglobal.com` on the Alpha server, cPanel user `dreamspo`,
Python 3.12.14 application already created at `/home/dreamspo/dreamspotglobal`.

Unlike the Vercel deployment, **uploaded files persist here** — student
documents, the logo, blog images and destination photography all survive.

---

## 1. Create the MySQL database

cPanel → **Database Wizard**

1. Database name: `dsg` → becomes `dreamspo_dsg`
2. Username: `dsg` → becomes `dreamspo_dsg`, set a strong password and save it
3. Privileges: tick **ALL PRIVILEGES**

---

## 2. Upload the code

cPanel → **Git Version Control** → Create, or use the File Manager.

- Clone URL: `https://github.com/austroboy/dream_spot_global.git`
- Repository path: `/home/dreamspo/dreamspotglobal`

If the folder already exists and is not empty, delete its contents first — the
Python app setup creates a `passenger_wsgi.py` and `tmp/` that the repository
will replace.

---

## 3. Environment variables

cPanel → **Setup Python App** → your application → **Environment variables**

| Name | Value |
|---|---|
| `DJANGO_ENV` | `production` |
| `SECRET_KEY` | a long random string |
| `DATABASE_URL` | `mysql://dreamspo_dsg:PASSWORD@localhost:3306/dreamspo_dsg` |
| `ALLOWED_HOSTS` | `dreamspotglobal.com,www.dreamspotglobal.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://dreamspotglobal.com,https://www.dreamspotglobal.com` |

URL-encode any of these characters in the password: `@` → `%40`, `:` → `%3A`,
`/` → `%2F`, `#` → `%23`.

Click **SAVE**, then **RESTART**.

---

## 4. Install and migrate

cPanel → **Terminal** (or SSH). Enter the virtual environment with the command
shown at the top of the Python App page:

```bash
source /home/dreamspo/virtualenv/dreamspotglobal/3.12/bin/activate && cd /home/dreamspo/dreamspotglobal

pip install --upgrade pip
pip install -r requirements-cpanel.txt

python manage.py migrate
python manage.py seed_demo --minimal      # destinations, services, pages, email templates
python manage.py createsuperuser          # your own admin login
python manage.py collectstatic --noinput
```

`seed_demo --minimal` loads only reference data — no demo leads or fake students.

Then restart the app: Python App page → **RESTART**.

---

## 5. Point the domain

At your domain registrar, set the nameservers to:

```
nsbd1.hostseba.com
nsbd2.hostseba.com
```

Propagation takes up to 48 hours. Until then use the temporary URL from the
welcome email to check the site.

---

## 6. Turn on HTTPS

Once the domain resolves: cPanel → **SSL/TLS Status** → select both
`dreamspotglobal.com` and `www` → **Run AutoSSL**.

After the certificate is issued, add one more environment variable and restart:

| Name | Value |
|---|---|
| `SECURE_SSL_REDIRECT` | `True` |

---

## 7. Business email (fixes the spam problem)

cPanel → **Email Accounts** → create `info@dreamspotglobal.com`.

Then add these environment variables and restart:

| Name | Value |
|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `mail.dreamspotglobal.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | `info@dreamspotglobal.com` |
| `EMAIL_HOST_PASSWORD` | the mailbox password |
| `EMAIL_USE_TLS` | `True` |
| `DEFAULT_FROM_EMAIL` | `Dream Spot Global <info@dreamspotglobal.com>` |
| `NOTIFY_EMAILS` | `dreamspotglobal@gmail.com` |

Sending from your own domain instead of Gmail is what keeps enquiry
confirmations out of the spam folder.

---

## 8. Scheduled jobs

cPanel → **Cron Jobs**:

```
*/15 * * * *  /home/dreamspo/virtualenv/dreamspotglobal/3.12/bin/python /home/dreamspo/dreamspotglobal/manage.py send_reminders
0 2 * * *     /home/dreamspo/virtualenv/dreamspotglobal/3.12/bin/python /home/dreamspo/dreamspotglobal/manage.py lead_housekeeping
0 3 * * *     /home/dreamspo/virtualenv/dreamspotglobal/3.12/bin/python /home/dreamspo/dreamspotglobal/manage.py expire_scholarships
```

---

## Deploying changes later

```bash
cd /home/dreamspo/dreamspotglobal
git pull
source /home/dreamspo/virtualenv/dreamspotglobal/3.12/bin/activate
pip install -r requirements-cpanel.txt
python manage.py migrate
python manage.py collectstatic --noinput
touch tmp/restart.txt          # tells Passenger to reload
```

---

## Troubleshooting

**"It works!" or a blank page** — Passenger has not picked up the app. Check
that `passenger_wsgi.py` is in the application root and press RESTART.

**500 error** — read `/home/dreamspo/dreamspotglobal/stderr.log`, or cPanel →
Errors. Nearly always `DATABASE_URL` or `SECRET_KEY`.

**`Can't connect to MySQL server`** — the password needs URL-encoding, or the
user was not granted ALL PRIVILEGES on the database.

**Site loads unstyled** — run `collectstatic` and restart.

**CSRF verification failed** — `CSRF_TRUSTED_ORIGINS` must include the
`https://` prefix.

---

## If MySQL gives trouble

The project also runs on PostgreSQL unchanged. The Neon database created for
the Vercel deployment still exists and already holds data; swapping back is one
environment variable:

```
DATABASE_URL=postgresql://neondb_owner:...@ep-...neon.tech/neondb?sslmode=require
```

and `pip install "psycopg[binary]"`.
