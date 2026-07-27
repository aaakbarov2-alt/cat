# cPanel deployment

## Hosting requirements

- cPanel **Setup Python App** (Phusion Passenger)
- Python 3.12 or newer
- SSH or cPanel Terminal access
- PostgreSQL or MariaDB/MySQL; SQLite can be used only for a small single-server launch
- A working SMTP mailbox or external SMTP provider

## 1. Upload the application

Create a folder such as `ielts_mock` outside `public_html` when the host permits it. Upload and extract the cPanel release package into that folder. Do not upload a development `.env`, `db.sqlite3`, backups, or local media.

## 2. Create the Python application

In **Setup Python App**, create an application with:

- Python version: 3.12 or newer
- Application root: `ielts_mock`
- Application URL: the intended domain or subdomain
- Startup file: `passenger_wsgi.py`
- Entry point: `application`

Save the virtual-environment activation command displayed by cPanel.

## 3. Install dependencies

Open cPanel Terminal, activate the application virtual environment, change to the application root, then run:

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Use the environment-variable section in **Setup Python App** when available. Otherwise create a private `.env` in the application root with permissions `600`.

Required production values:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
DJANGO_TRUST_PROXY_HEADERS=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=3600
DJANGO_ACCOUNT_EMAIL_VERIFICATION=mandatory
DATABASE_URL=mysql://CPANEL_USER:PASSWORD@localhost/CPANEL_DATABASE
DJANGO_DB_SSL_REQUIRE=False
DJANGO_EMAIL_HOST=smtp.example.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=mailbox@example.com
DJANGO_EMAIL_HOST_PASSWORD=replace-with-mailbox-password
DJANGO_EMAIL_USE_TLS=True
DJANGO_DEFAULT_FROM_EMAIL=IELTS Mock <mailbox@example.com>
DJANGO_SUPPORT_EMAIL=support@example.com
```

Do not enable HSTS subdomains or preload until every required subdomain is permanently HTTPS-only.
For a remote PostgreSQL provider, use its PostgreSQL URL and set `DJANGO_DB_SSL_REQUIRE=True`. For cPanel's local MySQL/MariaDB service, SSL is normally disabled because the connection never leaves the server.

## 5. Initialize Django

With the virtual environment active:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_practice_library
python manage.py createsuperuser
python manage.py check --deploy
```

## 6. Configure static and media URLs

The application serves versioned static files through WhiteNoise. For uploaded listening audio, create a `/media/` mapping from the domain document root to the application's `media` directory. With SSH this is normally a symbolic link similar to:

```bash
ln -s /home/CPANEL_USER/ielts_mock/media /home/CPANEL_USER/public_html/media
```

Replace both paths with the real application root and the real document root shown in cPanel. If the host blocks symbolic links, configure the mapping through cPanel support or use external object storage.

## 7. Enable HTTPS and restart

Enable AutoSSL for the domain in cPanel, confirm HTTPS works, and restart the Python application from **Setup Python App**. Then verify:

- `/health/` returns HTTP 200
- `/`, `/accounts/login/`, `/accounts/signup/`, and `/accounts/dashboard/`
- `/admin/`
- password-reset delivery
- contact-form delivery

## Updating later

Back up the database and media, upload the new files, activate the virtual environment, run migrations and static collection, then restart the Python application.
