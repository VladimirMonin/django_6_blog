#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --dry-run ]]; then
    export RESTORE_DRY_RUN=1
    shift
fi
[[ "${1:-}" == --target-file && -n "${2:-}" && "${3:-}" == --backup-id && -n "${4:-}" && $# -eq 4 ]] || { echo "usage: $0 --target-file FILE --backup-id ID" >&2; exit 2; }
target_file=$2
backup_id=$4
[[ "$backup_id" =~ ^[0-9]{8}T[0-9]{6}Z(-[a-z0-9]+)?$ ]] || { echo 'invalid backup id' >&2; exit 2; }
: "${BACKUP_MEDIA_DESTINATION:?}" "${RESTORE_AGE_IDENTITY_FILE:?}" "${RESTORE_SCRATCH_DIR:?}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
snapshot=$(mktemp)
trap 'rm -f -- "$snapshot"' EXIT
"$SCRIPT_DIR/verify-restored-state.py" --snapshot "$snapshot" \
    --hold-exec "$target_file" -- "$SCRIPT_DIR/execute-restore.sh" "$snapshot" "$target_file" "$backup_id"
