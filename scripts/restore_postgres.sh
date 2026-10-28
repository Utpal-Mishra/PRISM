#!/bin/sh
set -eu

: "${PGHOST:?PGHOST is required}"
: "${PGDATABASE:?PGDATABASE is required}"
: "${PGUSER:?PGUSER is required}"
: "${BACKUP_PATH:?BACKUP_PATH is required}"

MANIFEST_PATH="${MANIFEST_PATH:-${BACKUP_PATH}.sha256}"

test -f "$BACKUP_PATH"
test -f "$MANIFEST_PATH"
sha256sum -c "$MANIFEST_PATH"

pg_restore   --clean   --if-exists   --no-owner   --no-acl   --dbname="$PGDATABASE"   "$BACKUP_PATH"

printf 'restored=%s\n' "$BACKUP_PATH"
