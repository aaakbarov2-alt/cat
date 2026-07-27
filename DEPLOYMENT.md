# IELTS Mock deployment runbook

## Before the first deployment

1. Create a private `.env` from `.env.example`.
2. Generate a long random `DJANGO_SECRET_KEY`.
3. Set `DJANGO_DEBUG=False`.
4. Set the real domain in `DJANGO_ALLOWED_HOSTS` and HTTPS origins in `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. Set a strong PostgreSQL password and production `DATABASE_URL`.
6. Configure all `DJANGO_EMAIL_*` values and send a real password-reset test.
7. Keep `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False` and `DJANGO_SECURE_HSTS_PRELOAD=False` until every required subdomain is confirmed HTTPS-only.
8. Create the first administrator with `python manage.py createsuperuser` inside the deployed web container.

## Release procedure

1. Run `powershell -ExecutionPolicy Bypass -File scripts/check_deployment.ps1` locally.
2. Back up the current production database and media.
3. Build and deploy the new image.
4. The container entrypoint runs migrations and `collectstatic` before Gunicorn starts.
5. Confirm `/health/` returns HTTP 200.
6. Check `/`, `/accounts/login/`, `/faq/`, `/contact/`, and `/admin/`.
7. Submit a contact message and password-reset request.
8. Review application and proxy logs for errors.

The repository is deployment-ready, but the final upload requires the chosen host, public domain, PostgreSQL credentials, SMTP credentials, and DNS/HTTPS access. Never commit these values to the repository.

## Backups

- Windows Docker host: `powershell -ExecutionPolicy Bypass -File scripts/backup_docker.ps1`
- Linux/macOS Docker host: `sh scripts/backup_docker.sh`
- Local SQLite development copy: `powershell -ExecutionPolicy Bypass -File scripts/backup_local.ps1`
- Store copies outside the server and test restoration regularly.
- Never consider a backup reliable until a restoration test succeeds.

## Routine operations

- Monitor `/health/` and HTTPS certificate expiration.
- Review error logs and disk usage.
- Apply dependency/security updates through a tested deployment.
- Verify automated backups and keep more than one retention point.
- Do not edit production data directly unless a backup has been confirmed.

## Rollback

1. Stop routing new traffic to the failed release.
2. Redeploy the previously working image.
3. Restore the database only if the migration or release changed data incompatibly.
4. Restore media independently if uploaded files were affected.
5. Run `/health/` and the release smoke checks before reopening traffic.
