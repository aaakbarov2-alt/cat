$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $PSScriptRoot "..\backups\$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "ielts_mock" }
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "ielts_mock" }

docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc -f /tmp/ielts-mock.dump
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose cp "db:/tmp/ielts-mock.dump" (Join-Path $backupDir "database.dump")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose exec -T db rm -f /tmp/ielts-mock.dump

docker compose exec -T web tar -czf /tmp/ielts-media.tar.gz -C /app media
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose cp "web:/tmp/ielts-media.tar.gz" (Join-Path $backupDir "media.tar.gz")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose exec -T web rm -f /tmp/ielts-media.tar.gz

Write-Host "Backup completed: $backupDir"
