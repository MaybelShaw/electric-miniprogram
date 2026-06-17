#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.prod.yaml}"
MEDIA_DIR="${MEDIA_DIR:-${PROJECT_ROOT}/backend/backend/media}"
YES=0
START_SERVICES=1
BACKUP_DIR=""

usage() {
  cat <<'USAGE'
Usage: bash deploy/restore_production.sh <backup-dir> --yes [--no-start]

Restores:
  <backup-dir>/database.dump  -> PostgreSQL via pg_restore
  <backup-dir>/media.tar.gz   -> host media directory

Environment overrides:
  PROJECT_ROOT   Repository root. Default: parent of deploy/
  COMPOSE_FILE   Compose file relative to PROJECT_ROOT, or absolute path.
                 Default: docker/docker-compose.prod.yaml
  MEDIA_DIR      Host media directory to restore.
                 Default: $PROJECT_ROOT/backend/backend/media

Safety:
  --yes is required.
  Current MEDIA_DIR is moved aside to MEDIA_DIR.rollback-<timestamp>.
  backend/nginx/merchant-build are stopped before restore.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)
      YES=1
      shift
      ;;
    --no-start)
      START_SERVICES=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -n "${BACKUP_DIR}" ]]; then
        echo "Only one backup directory can be provided." >&2
        exit 1
      fi
      BACKUP_DIR="$1"
      shift
      ;;
  esac
done

if [[ -z "${BACKUP_DIR}" || "${YES}" -ne 1 ]]; then
  usage
  exit 1
fi

if [[ "${BACKUP_DIR}" != /* ]]; then
  BACKUP_DIR="$(cd "${BACKUP_DIR}" && pwd)"
fi

if [[ "${COMPOSE_FILE}" != /* ]]; then
  COMPOSE_PATH="${PROJECT_ROOT}/${COMPOSE_FILE}"
else
  COMPOSE_PATH="${COMPOSE_FILE}"
fi

DB_DUMP="${BACKUP_DIR}/database.dump"
MEDIA_ARCHIVE="${BACKUP_DIR}/media.tar.gz"

if [[ ! -f "${COMPOSE_PATH}" ]]; then
  echo "Compose file not found: ${COMPOSE_PATH}" >&2
  exit 1
fi

if [[ ! -f "${DB_DUMP}" ]]; then
  echo "Database dump not found: ${DB_DUMP}" >&2
  exit 1
fi

if [[ ! -f "${MEDIA_ARCHIVE}" ]]; then
  echo "Media archive not found: ${MEDIA_ARCHIVE}" >&2
  exit 1
fi

compose() {
  docker compose -f "${COMPOSE_PATH}" "$@"
}

echo "Restoring from: ${BACKUP_DIR}"
echo "Stopping application services..."
compose stop backend nginx merchant-build

echo "Restoring database..."
compose exec -T db sh -c 'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 --command "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"'
compose exec -T db sh -c 'pg_restore --exit-on-error --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' < "${DB_DUMP}"

echo "Restoring media files..."
ROLLBACK_MEDIA_DIR="${MEDIA_DIR}.rollback-$(date +%Y%m%d-%H%M%S)"
MEDIA_PARENT="$(dirname "${MEDIA_DIR}")"
mkdir -p "${MEDIA_PARENT}"

if [[ -e "${MEDIA_DIR}" ]]; then
  mv "${MEDIA_DIR}" "${ROLLBACK_MEDIA_DIR}"
  echo "Previous media moved to: ${ROLLBACK_MEDIA_DIR}"
fi

mkdir -p "${MEDIA_DIR}"
tar -xzf "${MEDIA_ARCHIVE}" -C "${MEDIA_DIR}"

if [[ "${START_SERVICES}" -eq 1 ]]; then
  echo "Starting application services..."
  compose up -d backend merchant-build nginx
else
  echo "Skipped service start because --no-start was provided."
fi

echo "Restore completed."
