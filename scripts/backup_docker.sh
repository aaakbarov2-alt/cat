#!/bin/sh
set -eu

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="./backups/$timestamp"
mkdir -p "$backup_dir"
db_user="${POSTGRES_USER:-ielts_mock}"
db_name="${POSTGRES_DB:-ielts_mock}"

docker compose exec -T db pg_dump -U "$db_user" -d "$db_name" -Fc -f /tmp/ielts-mock.dump
docker compose cp db:/tmp/ielts-mock.dump "$backup_dir/database.dump"
docker compose exec -T db rm -f /tmp/ielts-mock.dump

docker compose exec -T web tar -czf /tmp/ielts-media.tar.gz -C /app media
docker compose cp web:/tmp/ielts-media.tar.gz "$backup_dir/media.tar.gz"
docker compose exec -T web rm -f /tmp/ielts-media.tar.gz

echo "Backup completed: $backup_dir"
