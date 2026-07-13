#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
source "$SCRIPT_DIR/lib/safety.sh"

for name in BACKUP_STATE_DIR BACKUP_SCRATCH_DIR BACKUP_EVIDENCE_DIR BACKUP_LOCK_FILE BACKUP_SOURCE_PG_MAJOR BACKUP_EXECUTION_MODE BACKUP_AGE_RECIPIENT BACKUP_MEDIA_SOURCE BACKUP_MEDIA_DESTINATION; do require_var "$name"; done
for path in "$BACKUP_STATE_DIR" "$BACKUP_SCRATCH_DIR" "$BACKUP_EVIDENCE_DIR" "$BACKUP_LOCK_FILE"; do require_absolute "$path"; done
guard_execution_mode
preflight_tools

backup_id="${BACKUP_ID_OVERRIDE:-$(date -u +%Y%m%dT%H%M%SZ)}"
[[ "$backup_id" =~ ^[0-9]{8}T[0-9]{6}Z(-[a-z0-9]+)?$ ]] || die "invalid backup id"
work_dir="$BACKUP_SCRATCH_DIR/$backup_id"
evidence_dir="$BACKUP_EVIDENCE_DIR/$backup_id"
cleanup() { rm -rf -- "$work_dir"; rm -f -- "$BACKUP_STATE_DIR/last-success.tmp"; }
trap cleanup EXIT INT TERM

mkdir -p -- "$BACKUP_STATE_DIR" "$BACKUP_SCRATCH_DIR" "$BACKUP_EVIDENCE_DIR" "$(dirname -- "$BACKUP_LOCK_FILE")"
exec 9>"$BACKUP_LOCK_FILE"
flock -n 9 || die "backup already running" 3
mkdir -- "$work_dir"
printf '{"schema_version":1,"backup_id":"%s","status":"running"}\n' "$backup_id" > "$work_dir/manifest.json"

"$SCRIPT_DIR/postgres-backup.sh" "$backup_id" "$work_dir"
"$SCRIPT_DIR/media-backup.sh" "$backup_id" "$work_dir"
"$SCRIPT_DIR/verify-backup.sh" "$backup_id" "$work_dir"
mkdir -- "$evidence_dir"
cp -- "$work_dir/manifest.json" "$work_dir/checksums.sha256" "$evidence_dir/"
rclone copyto "$work_dir/postgres.dump.age" "$BACKUP_MEDIA_DESTINATION/$backup_id/postgres.dump.age"
rclone copyto "$work_dir/media.tar.age" "$BACKUP_MEDIA_DESTINATION/$backup_id/media.tar.age"
rclone copyto "$work_dir/manifest.json" "$BACKUP_MEDIA_DESTINATION/$backup_id/manifest.json"
rclone copyto "$work_dir/checksums.sha256" "$BACKUP_MEDIA_DESTINATION/$backup_id/checksums.sha256"
printf '%s\n' "$backup_id" | rclone rcat "$BACKUP_MEDIA_DESTINATION/$backup_id/SUCCESS"
printf '%s\n' "$backup_id" > "$BACKUP_STATE_DIR/last-success.tmp"
mv -- "$BACKUP_STATE_DIR/last-success.tmp" "$BACKUP_STATE_DIR/last-success"
trap - EXIT INT TERM
rm -rf -- "$work_dir"
printf 'backup %s completed\n' "$backup_id"
