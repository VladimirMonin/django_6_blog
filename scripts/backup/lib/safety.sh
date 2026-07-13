#!/usr/bin/env bash
set -euo pipefail

die() { printf '%s\n' "$1" >&2; exit "${2:-2}"; }
require_var() { [[ -n "${!1:-}" ]] || die "missing required variable: $1"; }
require_tool() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"; }
require_absolute() {
    [[ "$1" == /* && "$1" != / && "$1" != *'/../'* && "$1" != */.. ]] || die "unsafe path"
}
require_under() {
    local child parent
    child="$(realpath -m -- "$1")"; parent="$(realpath -m -- "$2")"
    [[ "$child" == "$parent"/* ]] || die "path escapes approved root"
}
semver_in_range() {
    local version="$1" minimum="$2" maximum="$3"
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    [[ "$(printf '%s\n%s\n' "$minimum" "$version" | sort -V | head -n1)" == "$minimum" ]] || return 1
    [[ "$version" != "$maximum" && "$(printf '%s\n%s\n' "$version" "$maximum" | sort -V | head -n1)" == "$version" ]]
}
tool_semver() {
    local output version
    output="$($1 --version 2>&1)" || die "cannot read $1 version"
    case "$1" in
        age) [[ "$output" =~ ^(age\ )?v?([0-9]+\.[0-9]+(\.[0-9]+)?)$ ]] || die "malformed $1 version"; version=${BASH_REMATCH[2]} ;;
        rclone) [[ "$output" =~ ^rclone\ v([0-9]+\.[0-9]+(\.[0-9]+)?)$ ]] || die "malformed $1 version"; version=${BASH_REMATCH[1]} ;;
        flock) [[ "$output" =~ ^flock\ from\ util-linux\ ([0-9]+\.[0-9]+(\.[0-9]+)?)$ ]] || die "malformed $1 version"; version=${BASH_REMATCH[1]} ;;
        *) die "unsupported version parser" ;;
    esac
    [[ "$version" == *.*.* ]] || version="${version}.0"
    printf '%s\n' "$version"
}
require_semver_range() {
    local version
    version="$(tool_semver "$1")"
    semver_in_range "$version" "$2" "$3" || die "unsupported $1 version"
}
postgres_major() {
    local output
    output="$($1 --version 2>&1)" || die "cannot read $1 version"
    [[ "$output" =~ ^(pg_dump|pg_restore)\ \(PostgreSQL\)\ ([0-9]+)(\.[0-9]+){1,2}$ ]] || die "malformed $1 version"
    printf '%s\n' "${BASH_REMATCH[2]}"
}
preflight_tools() {
    local dump_major restore_major
    for tool in pg_dump pg_restore age rclone flock sha256sum; do require_tool "$tool"; done
    dump_major="$(postgres_major pg_dump)"; restore_major="$(postgres_major pg_restore)"
    [[ "$dump_major" =~ ^(16|17|18)$ && "$dump_major" == "$restore_major" ]] || die "unsupported or mismatched PostgreSQL tools"
    [[ "$dump_major" == "$BACKUP_SOURCE_PG_MAJOR" ]] || die "PostgreSQL client/server major mismatch"
    require_semver_range age 1.2.0 2.0.0
    require_semver_range rclone 1.68.0 2.0.0
    require_semver_range flock 2.39.0 3.0.0
}

guard_execution_mode() {
    case "$BACKUP_EXECUTION_MODE" in
        fake)
            require_var BACKUP_OFFLINE_ROOT
            require_absolute "$BACKUP_OFFLINE_ROOT"
            for path in "$BACKUP_STATE_DIR" "$BACKUP_SCRATCH_DIR" "$BACKUP_EVIDENCE_DIR" "$BACKUP_LOCK_FILE"; do
                require_under "$path" "$BACKUP_OFFLINE_ROOT"
            done
            ;;
        live)
            require_var BACKUP_LIVE_APPROVAL_FILE
            [[ "$BACKUP_LIVE_APPROVAL_FILE" == /etc/django-6-blog/backup-live-approved ]] || die "unsafe live approval path"
            [[ -f "$BACKUP_LIVE_APPROVAL_FILE" && ! -L "$BACKUP_LIVE_APPROVAL_FILE" ]] || die "live backup is not approved"
            [[ "$(stat -c '%u:%a' "$BACKUP_LIVE_APPROVAL_FILE")" == "0:600" ]] || die "unsafe live approval file"
            ;;
        *) die "BACKUP_EXECUTION_MODE must be fake or live" ;;
    esac
}
