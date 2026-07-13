#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 3 ]] || { echo 'internal restore argument error' >&2; exit 2; }
snapshot=$1
target_file=$2
backup_id=$3
: "${RESTORE_DESCRIPTOR_JSON:?}" "${BACKUP_MEDIA_DESTINATION:?}" "${RESTORE_AGE_IDENTITY_FILE:?}" "${RESTORE_SCRATCH_DIR:?}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
source "$SCRIPT_DIR/../backup/lib/safety.sh"
for tool in age rclone pg_restore psql tar sha256sum python3; do require_tool "$tool"; done
require_semver_range age 1.2.0 2.0.0
require_semver_range rclone 1.68.0 2.0.0
readarray -t fields < <(python3 -c 'import json,os; d=json.loads(os.environ["RESTORE_DESCRIPTOR_JSON"]); print(d["target_kind"]); print(d["target_id"]); print(d["database_name"]); print(d["media_prefix"])')
target_kind=${fields[0]}; target_id=${fields[1]}; database_name=${fields[2]}; media_prefix=${fields[3]}
[[ -z "${RESTORE_REQUIRED_KIND:-}" || "$target_kind" == "$RESTORE_REQUIRED_KIND" ]] || { echo 'restore entry point does not own target kind' >&2; exit 2; }
[[ -r /dev/tty ]] || { echo 'restore requires /dev/tty' >&2; exit 2; }
printf 'Type RESTORE %s %s %s: ' "${target_kind^^}" "$target_id" "$backup_id" > /dev/tty
IFS= read -r phrase < /dev/tty || { echo 'restore confirmation unavailable' >&2; exit 2; }
[[ "$phrase" == "RESTORE ${target_kind^^} $target_id $backup_id" ]] || { echo 'restore confirmation mismatch' >&2; exit 2; }
work="$RESTORE_SCRATCH_DIR/$target_id-$backup_id"
[[ "$work" = /* && ! -e "$work" ]] || { echo 'unsafe restore scratch path' >&2; exit 2; }
mkdir -p -- "$work"
trap 'rm -rf -- "$work"' EXIT
for name in manifest.json checksums.sha256 SUCCESS; do
    rclone copyto "$BACKUP_MEDIA_DESTINATION/$backup_id/$name" "$work/$name"
done
[[ "$(cat "$work/SUCCESS")" == "$backup_id" ]] || { echo 'invalid SUCCESS marker' >&2; exit 3; }
manifest_major=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert set(d)=={"schema_version","backup_id","status","source_pg_major"}; assert d["schema_version"]==1 and d["backup_id"]==sys.argv[2] and d["status"]=="verified" and type(d["source_pg_major"]) is int; print(d["source_pg_major"])' "$work/manifest.json" "$backup_id") || { echo 'invalid backup manifest' >&2; exit 3; }
[[ "$manifest_major" =~ ^(16|17|18)$ && "$(postgres_major pg_restore)" == "$manifest_major" ]] || { echo 'PostgreSQL restore client/source major mismatch' >&2; exit 3; }
for name in postgres.dump.age media.tar.age; do
    rclone copyto "$BACKUP_MEDIA_DESTINATION/$backup_id/$name" "$work/$name"
done
(cd "$work" && sha256sum --check checksums.sha256)
age --decrypt --identity "$RESTORE_AGE_IDENTITY_FILE" --output "$work/postgres.dump" "$work/postgres.dump.age"
age --decrypt --identity "$RESTORE_AGE_IDENTITY_FILE" --output "$work/media.tar" "$work/media.tar.age"
# The parent verifier keeps descriptor/marker fds open until this process exits.
if [[ -n "${RESTORE_TEST_REPLACE_TARGET_WITH:-}" ]]; then
    [[ "${RESTORE_EXECUTION_MODE:-}" == fake && "$RESTORE_TEST_REPLACE_TARGET_WITH" = /* && -f "$RESTORE_TEST_REPLACE_TARGET_WITH" && ! -L "$RESTORE_TEST_REPLACE_TARGET_WITH" ]] || {
        echo 'unsafe restore mutation fixture' >&2
        exit 2
    }
    cp -- "$RESTORE_TEST_REPLACE_TARGET_WITH" "$target_file"
    chmod 0600 "$target_file"
fi
"$SCRIPT_DIR/verify-restored-state.py" --revalidate-held "$target_file" >/dev/null
[[ "$(psql --dbname "$database_name" --tuples-only --no-align -c "select count(*) from pg_catalog.pg_tables where schemaname not in ('pg_catalog','information_schema')")" == 0 ]] || { echo 'database target is not empty' >&2; exit 2; }
[[ -z "$(rclone lsf "$media_prefix" --max-depth 1)" ]] || { echo 'media target is not empty' >&2; exit 2; }
"$SCRIPT_DIR/verify-restored-state.py" --revalidate-held "$target_file" >/dev/null
if [[ "${RESTORE_DRY_RUN:-0}" == 1 ]]; then
    printf 'restore %s into %s validated (dry run)\n' "$backup_id" "$target_id"
    exit 0
fi
pg_restore --list "$work/postgres.dump" >/dev/null
"$SCRIPT_DIR/verify-restored-state.py" --revalidate-held "$target_file" >/dev/null
"$SCRIPT_DIR/verify-restored-state.py" --exec-held "$target_file" -- \
    pg_restore --exit-on-error --no-owner --no-acl --dbname "$database_name" "$work/postgres.dump"
"$SCRIPT_DIR/verify-restored-state.py" --revalidate-held "$target_file" >/dev/null
mkdir -- "$work/media"
tar -tf "$work/media.tar" >/dev/null
"$SCRIPT_DIR/verify-restored-state.py" --revalidate-held "$target_file" >/dev/null
tar -C "$work/media" -xf "$work/media.tar"
"$SCRIPT_DIR/verify-restored-state.py" --revalidate-held "$target_file" >/dev/null
"$SCRIPT_DIR/verify-restored-state.py" --exec-held "$target_file" -- \
    rclone copy "$work/media" "$media_prefix" --immutable --metadata
printf 'restore %s into %s completed\n' "$backup_id" "$target_id"