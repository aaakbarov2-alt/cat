$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $projectRoot "backups\local-$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$database = Join-Path $projectRoot "db.sqlite3"
if (Test-Path -LiteralPath $database) {
    Copy-Item -LiteralPath $database -Destination (Join-Path $backupDir "db.sqlite3")
}

$media = Join-Path $projectRoot "media"
if (Test-Path -LiteralPath $media) {
    Compress-Archive -LiteralPath $media -DestinationPath (Join-Path $backupDir "media.zip")
}

Write-Host "Local backup completed: $backupDir"
