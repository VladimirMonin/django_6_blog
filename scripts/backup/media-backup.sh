#!/usr/bin/env bash
set -euo pipefail
backup_id="$1"; work_dir="$2"
: "${BACKUP_MEDIA_SOURCE:?missing BACKUP_MEDIA_SOURCE}" "${BACKUP_MEDIA_DESTINATION:?missing BACKUP_MEDIA_DESTINATION}"
plain="$work_dir/media-plain"
mkdir -- "$plain"
trap 'rm -rf -- "$plain"' EXIT
rclone copy "$BACKUP_MEDIA_SOURCE" "$plain" --immutable --metadata
tar -C "$plain" -cf - . | age --recipient "$BACKUP_AGE_RECIPIENT" --output "$work_dir/media.tar.age"
[[ -s "$work_dir/media.tar.age" ]] || { echo "empty media archive" >&2; exit 4; }
rm -rf -- "$plain"
trap - EXIT
