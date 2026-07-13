#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
export RESTORE_REQUIRED_KIND=production
exec "$SCRIPT_DIR/run-restore.sh" "$@"
