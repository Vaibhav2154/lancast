#!/usr/bin/env bash
# Verify checksums and restore a LANCAST backup (NFR-REL-03).
#
# Usage:
#   ./infrastructure/scripts/restore.sh <BACKUP_DIR> [--target-db <DB_NAME>] --yes

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <BACKUP_DIR> [--target-db <DB_NAME>] --yes" >&2
  exit 2
fi

BACKUP_DIR="$1"
shift

TARGET_DB=""
CONFIRMED=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-db)
      TARGET_DB="${2:?Missing database name after --target-db}"
      shift 2
      ;;
    --yes)
      CONFIRMED=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$CONFIRMED" != true ]]; then
  echo "Refusing to restore without --yes confirmation." >&2
  exit 2
fi

if [[ ! -d "$BACKUP_DIR" || ! -f "$BACKUP_DIR/SHA256SUMS" ]]; then
  echo "Invalid backup directory (missing SHA256SUMS): $BACKUP_DIR" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

echo "Verifying SHA256SUMS..."
(
  cd "$BACKUP_DIR"
  sha256sum -c SHA256SUMS
)

if [[ -n "$TARGET_DB" ]]; then
  echo "Restoring PostgreSQL dump into verification database '$TARGET_DB'..."
  docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"'"$TARGET_DB"'\";" -c "CREATE DATABASE \"'"$TARGET_DB"'\";"'
  docker compose exec -T postgres sh -c 'pg_restore --no-owner -U "$POSTGRES_USER" -d "'"$TARGET_DB"'"' < "$BACKUP_DIR/postgres.dump"
  echo "Verification restore into '$TARGET_DB' succeeded."
  exit 0
fi

echo "Restoring primary PostgreSQL database..."
docker compose exec -T postgres sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$BACKUP_DIR/postgres.dump"

echo "Restoring uploaded files volume..."
docker compose exec -T api sh -c 'rm -rf /var/lib/lancast/uploads/* && tar -xzf - -C /var/lib/lancast/uploads' < "$BACKUP_DIR/uploads.tar.gz"

echo "Ensuring migrations are at head..."
docker compose exec -T api alembic upgrade head
echo "Primary restore complete."
