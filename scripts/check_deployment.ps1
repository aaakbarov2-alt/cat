$ErrorActionPreference = "Stop"
$env:DJANGO_DEBUG = "False"
$env:DJANGO_SECRET_KEY = "local-deployment-check-secret-with-more-than-fifty-characters-123456789"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://example.com"
$env:DJANGO_SECURE_HSTS_SECONDS = "3600"
$env:DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS = "True"
$env:DJANGO_SECURE_HSTS_PRELOAD = "True"

python manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python manage.py check --deploy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$env:DJANGO_DEBUG = "True"
$env:DJANGO_SECURE_SSL_REDIRECT = "False"
$env:DJANGO_ACCOUNT_EMAIL_VERIFICATION = "none"
python manage.py test
exit $LASTEXITCODE
