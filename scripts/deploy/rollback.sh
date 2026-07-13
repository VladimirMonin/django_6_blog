#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
: "${RELEASE_ROOT:?}" "${TARGET_RELEASE:?}"
acquire_deploy_lock

current=$(readlink -f -- "$RELEASE_ROOT/current") || die "current release is missing"
target="$RELEASE_ROOT/releases/$TARGET_RELEASE"
validate_release "$current"
validate_release "$target"
[[ -d "$target" ]] || die "target release is missing"

verdict_args=(
    --current "$current/release-metadata.json"
    --target "$target/release-metadata.json"
    --schema "$current/deploy/release-metadata.schema.json"
)
if [[ -n "${LIVE_MIGRATION_LEAVES_FILE:-}" ]]; then
    verdict_args+=(--live-leaves-file "$LIVE_MIGRATION_LEAVES_FILE")
else
    verdict_args+=(--project "$current")
fi
set +e
verdict=$("$current/.venv/bin/python" "$current/scripts/deploy/rollback_verdict.py" "${verdict_args[@]}")
verdict_status=$?
set -e
printf '%s\n' "$verdict"
[[ $verdict_status -eq 0 && "$verdict" == ALLOW_CODE_STATIC_ONLY ]] || exit 3

atomic_current "$target"
if [[ ${SKIP_READINESS:-0} != 1 ]] && ! readiness_check; then
    atomic_current "$current"
    die "rollback target failed readiness; current restored"
fi