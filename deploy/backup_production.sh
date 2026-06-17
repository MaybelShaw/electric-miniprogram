#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.prod.yaml}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/electric-miniprogram}"
MEDIA_DIR="${MEDIA_DIR:-${PROJECT_ROOT}/backend/backend/media}"
TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d-%H%M%S)}"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

usage() {
  cat <<'USAGE'
Usage: bash deploy/backup_production.sh

Environment overrides:
  PROJECT_ROOT   Repository root. Default: parent of deploy/
  COMPOSE_FILE   Compose file relative to PROJECT_ROOT, or absolute path.
                 Default: docker/docker-compose.prod.yaml
  BACKUP_ROOT    Directory to store backup snapshots.
                 Default: /var/backups/electric-miniprogram
  MEDIA_DIR      Host media directory to archive.
                 Default: $PROJECT_ROOT/backend/backend/media
  TIMESTAMP      Snapshot directory name. Default: current time.

Output:
  $BACKUP_ROOT/$TIMESTAMP/database.dump
  $BACKUP_ROOT/$TIMESTAMP/media.tar.gz
  $BACKUP_ROOT/$TIMESTAMP/manifest.txt
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${COMPOSE_FILE}" != /* ]]; then
  COMPOSE_PATH="${PROJECT_ROOT}/${COMPOSE_FILE}"
else
  COMPOSE_PATH="${COMPOSE_FILE}"
fi

if [[ ! -f "${COMPOSE_PATH}" ]]; then
  echo "Compose file not found: ${COMPOSE_PATH}" >&2
  exit 1
fi

if [[ ! -d "${MEDIA_DIR}" ]]; then
  echo "Media directory not found: ${MEDIA_DIR}" >&2
  echo "Set MEDIA_DIR to the current production media path if it differs." >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

compose() {
  docker compose -f "${COMPOSE_PATH}" "$@"
}

DB_DUMP="${BACKUP_DIR}/database.dump"
MEDIA_ARCHIVE="${BACKUP_DIR}/media.tar.gz"
MANIFEST="${BACKUP_DIR}/manifest.txt"

echo "Creating database backup..."
compose exec -T db sh -c 'pg_dump --format=custom --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' > "${DB_DUMP}"

echo "Creating media backup..."
tar -czf "${MEDIA_ARCHIVE}" -C "${MEDIA_DIR}" .

DB_NAME="$(compose exec -T db sh -c 'printf "%s" "$POSTGRES_DB"')"
DB_USER="$(compose exec -T db sh -c 'printf "%s" "$POSTGRES_USER"')"
GIT_COMMIT="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || true)"

{
  echo "created_at=$(date -Is)"
  echo "project_root=${PROJECT_ROOT}"
  echo "compose_file=${COMPOSE_PATH}"
  echo "git_commit=${GIT_COMMIT}"
  echo "database=${DB_NAME}"
  echo "database_user=${DB_USER}"
  echo "media_dir=${MEDIA_DIR}"
  echo "database_dump=database.dump"
  echo "media_archive=media.tar.gz"
} > "${MANIFEST}"

if command -v sha256sum >/dev/null 2>&1; then
  (
    cd "${BACKUP_DIR}"
    sha256sum database.dump media.tar.gz manifest.txt > SHA256SUMS
  )
fi

ln -sfn "${BACKUP_DIR}" "${BACKUP_ROOT}/latest"

echo "Backup completed: ${BACKUP_DIR}"
