#!/usr/bin/env bash
set -euo pipefail
ci_work=$(mktemp -d)
ci_prefix="bm-backup-ci-${GITHUB_RUN_ID:-local}"
cleanup() {
  docker compose -p "$ci_prefix-source" down -v >/dev/null 2>&1 || true
  docker compose -p "$ci_prefix-target" down -v >/dev/null 2>&1 || true
  rm -rf "$ci_work"
}
trap cleanup EXIT
export COMPOSE_PROJECT_NAME="$ci_prefix-source"
docker compose build backend backup-tools restore-tools
docker compose up -d --wait db
docker compose run --rm --no-deps backend python manage.py migrate --noinput >/dev/null
docker compose run --rm --no-deps backend python manage.py shell -c "from core.models import User; from pathlib import Path; User.objects.create_user('restore-fixture',email='restore@example.invalid',password='CI-only-password-2026'); Path('/app/data/fixture.bin').write_bytes(b'private fixture file')" >/dev/null
docker compose up -d --wait backend
openssl rand -base64 32 > "$ci_work/backup.key"
chmod 600 "$ci_work/backup.key"
python ops/backup.py backup --stack internal --target "$ci_work/backups" --key-file "$ci_work/backup.key"
ci_archive=$(find "$ci_work/backups" -name '*.bmbak' -print -quit)
export COMPOSE_PROJECT_NAME="$ci_prefix-target"
docker compose up -d --wait db
python ops/backup.py restore --stack internal --archive "$ci_archive" --destination "$ci_work/verified" --key-file "$ci_work/backup.key" --apply
# The restored application still has its explicit maintenance flag.
docker compose up -d --wait backend
docker compose exec -T backend python manage.py shell -c "from core.models import User; from core.maintenance import enabled; from pathlib import Path; assert User.objects.get(email='restore@example.invalid'); assert enabled(); assert Path('/app/data/fixture.bin').read_bytes()==b'private fixture file'"
# Existing installation is never overwritten by a second apply.
if python ops/backup.py restore --stack internal --archive "$ci_archive" --destination "$ci_work/rejected" --key-file "$ci_work/backup.key" --apply; then
  exit 1
fi
printf 'Encrypted PostgreSQL/file backup and empty-target restore passed.\n'
