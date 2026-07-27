# IELTS Mock Platform

## Local setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_practice_library
python manage.py createsuperuser
python manage.py runserver
```

Copy `.env.example` to `.env` before starting. Development defaults use SQLite and the console email backend.

## Production foundation

- Set `DJANGO_DEBUG=False` and provide a long, private `DJANGO_SECRET_KEY`.
- Set the public domain in `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Set `DATABASE_URL` to the production PostgreSQL connection string.
- Configure the `DJANGO_EMAIL_*` variables for password resets and email verification.
- Use persistent storage for uploaded media. WhiteNoise serves static assets only.
- Enable `DJANGO_TRUST_PROXY_HEADERS=True` only when the hosting proxy reliably sets `X-Forwarded-Proto`.
- Start HSTS conservatively and increase it after HTTPS is confirmed across required subdomains.

## Portable Docker deployment

1. Copy `.env.example` to `.env` and replace every production value, including `POSTGRES_PASSWORD`.
2. Run `docker compose up --build -d`.
3. The web container applies migrations, collects static assets, and starts Gunicorn.
4. Configure the load balancer or uptime monitor to check `/health/`.
5. Back up both the `postgres_data` and `media_data` volumes.

## Automated verification

- CI performs migration checks, Django's deployment audit, static collection, and the full test suite.
- On Windows, run `powershell -ExecutionPolicy Bypass -File scripts/check_deployment.ps1` before a release.
- Release, monitoring, backup, and rollback procedures are in `DEPLOYMENT.md`.
- Shared-hosting instructions for Phusion Passenger are in `CPANEL_DEPLOYMENT.md`.

## Main routes

- `/` - landing page
- `/accounts/login/` - login
- `/accounts/dashboard/` - student dashboard
- `/accounts/settings/` - student profile settings
- `/exams/` - mock-test catalogue
- `/admin/` - content administration
