#!/usr/bin/env bash
# Create a timestamped, checksummed backup of LANCAST PostgreSQL and uploaded files (NFR-REL-03).
#
# Usage:
#   ./infrastructure/scripts/backup.sh [OUTPUT_ROOT]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_ROOT="${1:-$ROOT_DIR/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST_DIR="$OUT_ROOT/lancast-backup-$STAMP"

mkdir -p "$DEST_DIR"
cd "$ROOT_DIR"

echo "Backing up PostgreSQL..."
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST_DIR/postgres.dump"

echo "Backing up uploaded files volume..."
docker compose exec -T api tar -czf - -C /var/lib/lancast/uploads . > "$DEST_DIR/uploads.tar.gz"

{
  echo "timestamp_utc=$STAMP"
  echo "git_head=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
} > "$DEST_DIR/metadata.txt"

(
  cd "$DEST_DIR"
  sha256sum postgres.dump uploads.tar.gz > SHA256SUMS
)

echo "Backup complete: $DEST_DIR"
ls -lh "$DEST_DIR"
