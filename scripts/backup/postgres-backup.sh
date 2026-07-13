#!/usr/bin/env bash
set -euo pipefail
backup_id="$1"; work_dir="$2"
: "${BACKUP_AGE_RECIPIENT:?missing BACKUP_AGE_RECIPIENT}"
archive="$work_dir/postgres.dump.age"
plain="$work_dir/postgres.dump"
trap 'rm -f -- "$plain"' EXIT
pg_dump --format=custom --no-owner --no-acl --file="$plain"
pg_restore --list "$plain" >/dev/null
age --recipient "$BACKUP_AGE_RECIPIENT" --output "$archive" "$plain"
[[ -s "$archive" ]] || { echo "empty PostgreSQL archive" >&2; exit 4; }
printf '%s  %s\n' "$(sha256sum "$archive" | cut -d' ' -f1)" "postgres.dump.age" > "$work_dir/postgres.sha256"
rm -f -- "$plain"
trap - EXIT
printf 'postgres backup %s prepared\n' "$backup_id"
