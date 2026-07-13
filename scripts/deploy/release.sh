#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
: "${RELEASE_ROOT:?}" "${SOURCE_DIR:?}" "${RELEASE_ID:?}" "${RELEASE_COMMIT:?}" "${RELEASE_CREATED_AT:?}" "${MIGRATION_SAFETY:?}" "${MEDIA_STORAGE_MODE:?}"
acquire_deploy_lock
release="$RELEASE_ROOT/releases/$RELEASE_ID"; validate_release "$release"; [[ ! -e "$release" ]] || die "release exists"
mkdir -p "$release"
previous=""
if [[ -L "$RELEASE_ROOT/current" ]]; then
    previous=$(readlink -f -- "$RELEASE_ROOT/current")
    validate_release "$previous"
fi
published=0
cleanup() {
    if [[ $published -eq 1 ]]; then
        if [[ -n "$previous" ]]; then
            atomic_current "$previous"
        elif [[ -L "$RELEASE_ROOT/current" && "$(readlink -f -- "$RELEASE_ROOT/current")" == "$release" ]]; then
            rm -f -- "$RELEASE_ROOT/current"
        fi
    fi
    rm -rf -- "$release"
}
finish() {
    local status=$?
    if [[ $status -ne 0 ]]; then
        trap - EXIT
        cleanup
    fi
    exit "$status"
}
trap finish EXIT
cp -a --no-preserve=ownership "$SOURCE_DIR/." "$release/"
static_root="$release/staticfiles"
[[ "$(realpath -m -- "$static_root")" == "$release/staticfiles" && ! -L "$static_root" ]] || die "unsafe static root"
[[ "$(realpath -m -- "$static_root")" != "$(realpath -m -- "$SOURCE_DIR")" ]] || die "unsafe static root"
if [[ -n "$previous" ]]; then
    [[ "$(realpath -m -- "$static_root")" != "$(realpath -m -- "$previous/staticfiles")" ]] || die "unsafe static root"
fi
(cd "$release" && uv sync --frozen && .venv/bin/python -c 'import sys; print(sys.executable)' >/dev/null && .venv/bin/python manage.py check && .venv/bin/python manage.py collectstatic --noinput)
[[ -d "$static_root" && ! -L "$static_root" ]] || die "static collection did not create a safe release-local root"
metadata_args=(
    --project "$release"
    --schema "$release/deploy/release-metadata.schema.json"
    --output "$release/release-metadata.json"
    --commit "$RELEASE_COMMIT"
    --created-at "$RELEASE_CREATED_AT"
    --migration-safety "$MIGRATION_SAFETY"
    --media-storage-mode "$MEDIA_STORAGE_MODE"
    --static-manifest "$release/staticfiles/staticfiles.json"
)
if [[ -n "$previous" ]]; then
    [[ -f "$previous/release-metadata.json" ]] || die "predecessor metadata is missing"
    metadata_args+=(--predecessor "$previous/release-metadata.json")
fi
"$release/.venv/bin/python" "$release/scripts/deploy/release_metadata.py" "${metadata_args[@]}"
[[ "$("$release/.venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["release_id"])' "$release/release-metadata.json")" == "$RELEASE_ID" ]] || die "release id does not match generated metadata"
"$release/.venv/bin/gunicorn" --check-config -c "$release/deploy/gunicorn.conf.py" config.wsgi:application
atomic_current "$release"
published=1
if [[ ${SKIP_READINESS:-0} != 1 ]]; then readiness_check; fi
trap - EXIT
