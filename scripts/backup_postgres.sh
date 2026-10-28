#!/bin/sh
set -eu

: "${PGHOST:?PGHOST is required}"
: "${PGDATABASE:?PGDATABASE is required}"
: "${PGUSER:?PGUSER is required}"

BACKUP_PATH="${BACKUP_PATH:-./backups/prism-$(date -u +%Y%m%dT%H%M%SZ).dump}"
MANIFEST_PATH="${BACKUP_PATH}.sha256"

mkdir -p "$(dirname "$BACKUP_PATH")"

pg_dump   --format=custom   --no-owner   --no-acl   --file="$BACKUP_PATH"

sha256sum "$BACKUP_PATH" > "$MANIFEST_PATH"

printf 'backup=%s\nmanifest=%s\n' "$BACKUP_PATH" "$MANIFEST_PATH"
