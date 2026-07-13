#!/usr/bin/env bash
set -euo pipefail
backup_id="$1"; work_dir="$2"
[[ -s "$work_dir/postgres.dump.age" && -s "$work_dir/media.tar.age" ]] || { echo "incomplete backup" >&2; exit 4; }
printf '{"schema_version":1,"backup_id":"%s","status":"verified","source_pg_major":%s}\n' "$backup_id" "$BACKUP_SOURCE_PG_MAJOR" > "$work_dir/manifest.json"
(cd "$work_dir" && sha256sum postgres.dump.age media.tar.age manifest.json > checksums.sha256)
