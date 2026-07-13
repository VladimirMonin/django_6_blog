#!/usr/bin/env bash
set -euo pipefail

die() { printf 'deploy: %s\n' "$1" >&2; exit 2; }

validate_release() {
    local path=$1 resolved root
    [[ "$path" = /* && ! -L "$path" ]] || die "unsafe release path"
    root=$(realpath -m -- "${RELEASE_ROOT:?}/releases")
    resolved=$(realpath -m -- "$path")
    [[ "$resolved" == "$root"/* && "$resolved" != "$root" ]] || die "unsafe release path"
}

acquire_deploy_lock() {
    mkdir -p -- "${RELEASE_ROOT:?}"
    exec 9>"$RELEASE_ROOT/.deploy.lock"
    flock -n 9 || die "another release operation is running"
}

atomic_current() {
    local target=$1 temporary="$RELEASE_ROOT/.current.$$"
    validate_release "$target"
    ln -s -- "$target" "$temporary"
    mv -Tf -- "$temporary" "$RELEASE_ROOT/current"
}

readiness_check() {
    local url=${READINESS_URL:-http://127.0.0.1:8036/api/v1/health/ready/}
    local attempts=${READINESS_ATTEMPTS:-5}
    local i
    [[ "$attempts" =~ ^[1-9][0-9]?$ ]] || die "invalid readiness attempt count"
    for ((i=1; i<=attempts; i++)); do
        if curl --fail --silent --show-error --max-time 5 --output /dev/null -- "$url"; then
            return 0
        fi
        [[ $i -eq $attempts ]] || sleep 1
    done
    return 1
}
