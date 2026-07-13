#!/usr/bin/env bash
set -euo pipefail
: "${BACKUP_MEDIA_DESTINATION:?missing BACKUP_MEDIA_DESTINATION}"
mode=${1:---dry-run}
[[ "$mode" == --dry-run || "$mode" == --execute ]] || { echo 'usage: prune-backups.sh [--dry-run|--execute]' >&2; exit 2; }
manifest=$(mktemp)
recheck=$(mktemp)
trap 'rm -f -- "$manifest" "$recheck"' EXIT
rclone lsf "$BACKUP_MEDIA_DESTINATION" --dirs-only | sed 's:/$::' | LC_ALL=C sort -u > "$manifest"
count=$(wc -l < "$manifest" | tr -d ' ')
digest=$(sha256sum "$manifest" | cut -d' ' -f1)
printf 'prune candidates=%s digest=%s\n' "$count" "$digest"
cat "$manifest"
[[ "$mode" == --execute ]] || exit 0
[[ -r /dev/tty ]] || { echo 'destructive prune requires /dev/tty' >&2; exit 2; }
printf 'Type PRUNE <backup_id> %s for exactly one listed backup: ' "$count" > /dev/tty
IFS= read -r phrase < /dev/tty || { echo 'prune confirmation unavailable' >&2; exit 2; }
[[ "$phrase" =~ ^PRUNE\ ([0-9]{8}T[0-9]{6}Z(-[a-z0-9]+)?)\ ([0-9]+)$ ]] || { echo 'prune confirmation mismatch' >&2; exit 2; }
backup_id=${BASH_REMATCH[1]}
confirmed_count=${BASH_REMATCH[3]}
[[ "$confirmed_count" == "$count" ]] || { echo 'candidate count changed' >&2; exit 2; }
grep -Fxq -- "$backup_id" "$manifest" || { echo 'backup is not a candidate' >&2; exit 2; }
rclone lsf "$BACKUP_MEDIA_DESTINATION" --dirs-only | sed 's:/$::' | LC_ALL=C sort -u > "$recheck"
[[ "$(sha256sum "$recheck" | cut -d' ' -f1)" == "$digest" ]] || { echo 'candidate manifest changed' >&2; exit 2; }
rclone purge "$BACKUP_MEDIA_DESTINATION/$backup_id"
printf 'pruned %s\n' "$backup_id"
