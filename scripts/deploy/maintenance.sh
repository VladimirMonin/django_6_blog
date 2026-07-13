#!/usr/bin/env bash
set -euo pipefail
instance=${1:-}
[[ "$instance" =~ ^(migrate|check|collectstatic):([0-9]{8}T[0-9]{6}Z-[0-9a-f]{12})$ ]] || { echo 'operation or release id not allowed' >&2; exit 2; }
op=${BASH_REMATCH[1]}
release_id=${BASH_REMATCH[2]}
release_root=${RELEASE_ROOT:-/srv/django-6-blog}
[[ "$release_root" = /* && ! -L "$release_root" ]] || { echo 'invalid release root' >&2; exit 2; }
release="$release_root/releases/$release_id"
resolved=$(realpath -e -- "$release") || { echo 'release is missing' >&2; exit 2; }
approved=$(realpath -m -- "$release_root/releases")
[[ "$resolved" == "$approved/$release_id" && ! -L "$release" ]] || { echo 'invalid release' >&2; exit 2; }
case "$op" in
    migrate) args=(migrate --noinput) ;;
    check) args=(check --deploy) ;;
    collectstatic) args=(collectstatic --noinput) ;;
esac
exec "$release/.venv/bin/python" "$release/manage.py" "${args[@]}"
