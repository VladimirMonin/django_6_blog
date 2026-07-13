# Offline production contract: B1–B9

Status: implementation specification for Stage 1 of `.hermes/plans/offline-production-readiness.md`.

This document closes the specification defects B1–B9 from review `t_7883fe6d`. It authorizes repository-only implementation and offline/CI verification. It does not authorize credentials, paid resources, SSH, DNS/TLS changes, remote PostgreSQL or S3 access, service installation/reload, deployment, backup, restore, or production data mutation.

## Global boundaries

### Canonical ownership

| Contract | Authoritative owner |
|---|---|
| local SQLite defaults and shared static aliases | `config/settings.py` |
| production validation, PostgreSQL, security, S3 override | `config/settings_production.py` |
| environment parsing primitives | `config/env.py` |
| dependency ranges | `pyproject.toml`; resolved versions in `uv.lock` |
| CI execution | `.github/workflows/ci.yml` |
| host-facing examples and scripts | `deploy/**`, `scripts/**` |
| operational procedures and live owner assignments | `doc/deployment.md`, `doc/backup-restore.md` |

`config.settings_production` imports the base settings, preserves `STORAGES["staticfiles"]`, and may override only `STORAGES["default"]`. Application code must not choose a production backend.

### Secret handling

Repository examples contain names and placeholders only. Tests use canary values and assert that the canary, database URL, auth material, rollback authorization input, and exception text do not occur in argv, stdout, stderr, generated metadata, or captured logs. Production secrets enter only through systemd `EnvironmentFile=` or an equivalent credential mechanism reviewed later; scripts must not source env files or accept secret values as command-line arguments.

### Offline/live split

Offline implementation may create or edit repository files, run local SQLite tests, use an ephemeral PostgreSQL service in CI, use fake/pathless storage backends, create temporary release trees, and statically validate Nginx/systemd/shell artifacts. It must not touch `/etc`, `/srv`, `/run`, a service manager, network services other than the isolated CI PostgreSQL service, or real credentials/endpoints.

All live actions remain a separate `needs_input` gate owned by Vladimir plus the named host/database/storage/backup operator. Passing this contract proves repository behavior only.

## B1 — final-path release virtualenv

**Files**

- create `scripts/deploy/lib.sh`, `scripts/deploy/release.sh`
- create `tests/test_deploy_artifacts.py`
- document in `doc/deployment.md`

**Behavior**

The release script creates `releases/<release-id>` at its final pathname before `uv sync`. It never builds a virtualenv below a directory that will be renamed. A temporary sibling may hold downloaded source, but source is copied into the final directory before `.venv` creation. The final directory is unpublished until all checks pass; publication is the atomic replacement of `/srv/django-6-blog/current` symlink. Pre-cutover failure removes only the newly created, positively validated release path and leaves `current` unchanged.

After the exact build sequence, the script executes final-path `.venv/bin/python -c ...` and `.venv/bin/gunicorn --check-config` with `deploy/gunicorn.conf.py`. Tests inspect console-script shebangs and prove they refer to the final release path, not `.incoming-*`.

**Dependencies**: the bounded Gunicorn dependency portion of B8. B2 consumes the final-path interface after B1; B1 does not depend on B2.

**Offline gate**: fake release root under `tmp_path`; successful final-path execution; injected failure before symlink exchange leaves prior target unchanged; no path outside the fake root changes.

**Rollback**: atomically repoint `current` to a retained compatible release. No migration reversal, DB restore, or media reversal is implicit.

**Live-only**: creation/permissions under `/srv`, real service reload/restart, real readiness probe.

## B2 — safe production command/environment boundary

**Files**

- create `deploy/systemd/django-6-blog-maintenance@.service`
- create `deploy/systemd/django-6-blog.env.example`
- create `scripts/deploy/maintenance.sh`
- cover in `tests/test_deploy_artifacts.py`
- document host path/ownership in `doc/deployment.md`

**Behavior**

The reviewed transient unit is the only production boundary for `migrate`, `check`, and `collectstatic`. It uses `EnvironmentFile=/etc/django-6-blog/django-6-blog.env`, `User=django-blog`, `Group=django-blog`, an explicit final release `WorkingDirectory`, and an allowlisted operation selected by the instance/wrapper. The env file is `root:django-blog 0640`; releases are root/deployer-owned and read-only to the application user except declared generated paths. The wrapper rejects unknown operations, relative release paths, symlinks outside the release root, and direct secret arguments.

The unit receives operation and validated release identifier only. It does not shell-source the env file and does not use `sh -c`. Management commands run via final-path `.venv/bin/python manage.py ...`.

**Dependencies**: B1 release layout and the release-metadata schema from B8. Implement B8's schema before B2; no cycle is permitted.

**Offline gate**: artifact assertions for user/group/environment/working directory; fake `systemd-run`/command harness proves allowlist and argv; canary secret absent from output/log capture; dry run touches neither host paths nor services.

**Rollback**: maintenance command failure stops before cutover. A successful migration follows B8 compatibility rules and is not automatically reversed.

**Live-only**: installing unit/env file, assigning host permissions, invoking systemd.

## B3 — production settings, PostgreSQL, and truthful readiness

**Files**

- create `config/settings_production.py`, `tests/test_production_settings.py`
- modify `config/env.py`, `pyproject.toml`, `uv.lock`, `.env.example`
- modify `.github/workflows/ci.yml`
- modify `api/views.py`, `api/urls.py`, `blog/test_infra.py`

**Behavior**

Production settings fail closed unless `DJANGO_DEBUG=false`, a non-placeholder `DJANGO_SECRET_KEY` is present, hosts contain no wildcard, CSRF origins are valid HTTPS origins, and `DATABASE_URL` uses PostgreSQL. Add the exact direct-dependency ranges `psycopg[binary]>=3.2,<4` and `dj-database-url>=3,<4`; `uv.lock` must resolve versions inside those half-open ranges. PostgreSQL options include `connect_timeout=2`; every connection initializes `statement_timeout=2000` milliseconds. Base `config.settings` remains SQLite-compatible.

Expose `GET /api/v1/health/live/` without DB access and `GET /api/v1/health/ready/` using `SELECT 1`; legacy `/api/v1/health/` mirrors readiness for one rollout. All are GET-only, unauthenticated, low-information, and `Cache-Control: no-store`. Liveness returns 200. Readiness returns 200 only after DB success and sanitized 503 on failure; logs use stable fields without DSN, credentials, or exception text.

CI adds a separate PostgreSQL service job with fixed non-secret CI credentials and healthcheck. It runs migrations, Django check, and readiness tests against PostgreSQL. A failed-connection subprocess test proves readiness returns 503 within a bounded test timeout.

**Dependencies**: none for implementation; B4 S3 validation composes with production settings later.

**Offline gate**: subprocess matrix for missing/invalid env; `check --deploy` exits 0 with zero warnings under dummy valid env; local SQLite regression passes; CI PostgreSQL migrations/check/readiness pass; failed readiness is 503 within bound.

**Rollback**: revert settings/dependencies/routes; no offline schema mutation beyond disposable CI DB. Live migration rollback is governed by B8.

**Live-only**: Timeweb DB credentials/network, real outage test, monitor configuration.

## B4 — complete `STORAGES` and fail-closed production media

**Files**

- modify `config/settings.py`, `config/settings_production.py`, `config/env.py`, `.env.example`
- modify `pyproject.toml`, `uv.lock`
- create/extend `tests/test_production_settings.py`, `blog/test_storage_compat.py`

**Behavior**

Base settings define both aliases: local filesystem `default` and `ManifestStaticFilesStorage` for `staticfiles`; they define `STATIC_ROOT`. Production preserves the static alias. `DJANGO_MEDIA_STORAGE` has an explicit production value `s3`; production refuses missing/other values and refuses incomplete S3 configuration instead of falling back to filesystem.

Canonical names are `MEDIA_S3_ENDPOINT_URL`, `MEDIA_S3_BUCKET_NAME`, `MEDIA_S3_REGION_NAME`, `MEDIA_S3_AUTH_ID`, `MEDIA_S3_AUTH_MATERIAL`, `MEDIA_S3_CUSTOM_DOMAIN`, `MEDIA_S3_SIGNED_URLS`, `MEDIA_S3_SIGNED_URL_TTL_SECONDS`, `MEDIA_S3_CACHE_CONTROL`, `MEDIA_S3_FILE_OVERWRITE`, `MEDIA_S3_ADDRESSING_STYLE`, `MEDIA_S3_SIGNATURE_VERSION`, and `MEDIA_S3_VERIFY_SSL`. Tests reject stale `S3_*` aliases. Add the exact direct-dependency range `django-storages[s3]>=1.14.6,<2`; `uv.lock` must resolve a version inside that half-open range. Direct `boto3` is added only if application code imports it.

**Dependencies**: B3 production settings. B4 provides aliases to B9; it does not depend on B9 or B6.

**Offline gate**: subprocess assertions for both aliases in local and production modules; missing S3 values fail before Django startup; no network call during settings import; canonical/stale-name tests pass.

**Rollback**: path-free code lands while filesystem remains active. Backend switching is live-only and requires B5 key-preserving copy/rebuild evidence.

**Live-only**: bucket creation/configuration, credentials, object writes, ACL/CORS/cache validation.

## B5 — atomic path-free thumbnails and persisted HTML rebuild

**Files**

- modify `blog/models.py`
- create `blog/test_storage_compat.py`
- create `blog/management/commands/rebuild_content_html.py`
- create `blog/migrations/0012_postmedia_thumbnail_paths.py` only if post-scoped derivative keys require field-state migration
- update affected media/import tests during implementation

**Behavior**

Thumbnail generation opens the source once, decodes once, and creates both derivatives in memory without `FieldFile.path`. Derivative keys are post-scoped and deterministic. Save is compensating-atomic: track objects created by this attempt; if any storage write or DB field update fails, delete only those newly created objects, clear unsaved field names, log a sanitized structured failure, and allow an idempotent retry. Never delete a pre-existing referenced object. Corrupt images are skipped with a sanitized warning; remote read/write failures are not silent.

`rebuild_content_html` reports candidates/changed/skipped/errors, supports `--dry-run`, writes zero rows in dry run, processes bounded batches, and is idempotent. Its rollback policy is explicit: persisted URLs are regenerated according to the currently active storage URL policy; previous HTML is not silently reconstructed from stale URLs.

**Dependencies**: B4 storage contract.

**Offline gate**: pathless backend whose `path()` raises; source-open count equals one; dimensions verified; second-write failure leaves no orphan and empty DB fields; DB-update failure compensates both new objects; retry succeeds; duplicate names remain isolated; rebuild dry run writes zero, first real run changes expected rows, second changes zero.

**Rollback**: deploy path-free code before switching storage. Filesystem rollback after live cutover requires reverse-sync of every post-cutover key and a rebuild under restored URL policy.

**Live-only**: S3 copy/delta sync, checksums/counts, real Range/CORS/cache behavior, backend cutover.

## B6 — complete Nginx trusted boundary

**Files**

- create `deploy/nginx/django-6-blog.conf.example`
- create `blog/test_static_delivery.py` or validate within `tests/test_deploy_artifacts.py`
- align `config/settings_production.py`, `.env.example`, `doc/deployment.md`

**Behavior**

The example contains separate HTTP redirect and HTTPS server blocks with placeholders, never real certificate/domain paths. It overwrites (not appends) `Host`, `X-Forwarded-Proto`, and forwarding headers; proxies only to `/run/django-6-blog/gunicorn.sock`; preserves upstream 503 responses; defines request-body size; serves slash-safe release-local static alias with distinct hashed immutable and unhashed revalidation cache policy; never falls back static requests to Gunicorn. Trusted proxy settings are enabled only with this boundary.

The repository names the host/TLS operator and requires certificate insertion plus `nginx -t` before reload. HSTS activation is a later explicit live decision after HTTPS verification.

**Dependencies**: B3 security settings, B9 static manifest, B1 release layout.

**Offline gate**: text/structure assertions for redirect, TLS placeholders, proxy overwrite semantics, socket, size, 503, aliases and cache classes; optional `nginx -t` only against a generated temporary config if Nginx exists.

**Rollback**: validate previous config, switch symlink/config atomically, run `nginx -t`, then reload. Keep previous release static tree.

**Live-only**: certificate/domain insertion, host install, reload, TLS/HSTS validation.

## B7 — executable backup orchestrator and host-state contract

**Files**

- create `scripts/backup/run-backup.sh`, `scripts/backup/lib/safety.sh`, component backup/verify/prune scripts
- create restore scripts and `scripts/restore/verify-restored-state.py`
- create backup service/timer/env example under `deploy/systemd/`
- create `tests/test_backup_script_safety.py`
- create `doc/backup-restore.md`; link from `doc/infrastructure.md`, `doc/README.md`

**Behavior**

`run-backup.sh` is the sole service `ExecStart`. Canonical host paths are `/var/lib/django-6-blog-backup/{scratch,state,evidence}`, `/run/lock/django-6-blog-backup.lock`, and `/var/lib/django-6-blog-backup/state/last-success`. The unit declares writable paths explicitly and otherwise hardens filesystem access. One `backup_id` binds encrypted PostgreSQL archive, encrypted off-server media copy, manifest, checksums, and remote `SUCCESS` marker.

Preflight runs before side effects and parses numeric tool versions. The supported matrix is: `pg_dump` and `pg_restore` major `16`, `17`, or `18`; `age >=1.2.0,<2.0.0`; `rclone >=1.68.0,<2.0.0`; and util-linux `flock >=2.39.0,<3.0.0`. PostgreSQL tools must have the same major as each other and exactly equal the source server major recorded in metadata; no implicit cross-major support is claimed. Tests cover each lower bound, the greatest representable version below each upper bound, one value below/at the upper boundary, malformed output, and PostgreSQL client/server mismatch. Missing or unsupported tools/variables fail closed before side effects.

Prune is dry-run by default. Destructive prune is accepted only on an interactive TTY read directly from `/dev/tty` after the candidate manifest is printed; the operator must type the exact non-secret phrase `PRUNE <backup_id> <candidate_count>`. The phrase is never accepted through argv, environment, stdin redirection, or a file. Missing/non-TTY input, EOF, phrase mismatch, changed candidate count, or changed manifest digest refuses before deletion; the candidate set and digest are recomputed after confirmation.

Restore is TTY-only, maintenance-gated, never timer-driven, and receives an absolute `--target-file` path whose UTF-8 JSON object has exactly these fields: `schema_version` (integer `1`), `target_kind` (enum `disposable`, `production`), `target_id` (string matching `^[a-z0-9][a-z0-9-]{2,62}$`), `database_name` (string matching `^[A-Za-z_][A-Za-z0-9_]{0,62}$`), `media_prefix` (non-empty normalized relative POSIX prefix with no `.`/`..` segment), `expected_database_empty` (boolean), `expected_media_empty` (boolean), and `maintenance_marker` (absolute regular-file path beneath `/run/django-6-blog/restore-maintenance/`). Additional fields are rejected. The target file must be a non-symlink regular file owned by the invoking uid, mode `0600`, and opened once by file descriptor before validation; its content must contain no credential, DSN, endpoint, or key material. Both expected-empty fields must be `true` and independently verified immediately before writes. `production` additionally requires the maintenance marker to exist, be a non-symlink root-owned mode-`0600` regular file containing exactly `target_id`, plus direct `/dev/tty` confirmation `RESTORE PRODUCTION <target_id> <backup_id>`; `disposable` requires confirmation `RESTORE DISPOSABLE <target_id> <backup_id>`. Any mismatch, non-TTY execution, stale marker, non-empty target, or target identity change refuses before DB/media writes.

Named operational roles in docs: backup operator owns monitoring/pruning; database and storage operators own source access; security/key custodian owns age-key rotation/recovery; Vladimir is change approver; restore commander coordinates break-glass restore. Monthly disposable rehearsal records sanitized RPO/RTO evidence.

**Dependencies**: B3 PostgreSQL contract and B8 compatibility metadata schema.

**Offline gate**: shell syntax; fake binaries and temporary roots; failure injection at every phase; exact tool-boundary matrix; missing variables/tools cause zero side effects; lock/status/last-success behavior; service-to-orchestrator match; prune TTY phrase and manifest-race assertions; restore schema/ownership/mode/marker/emptiness/TTY matrix; dry-run prune/restore writes/deletes nothing; canary secrets absent.

**Rollback**: backup implementation has no application mutation. Restore is not deploy rollback and requires a separate live approval.

**Live-only**: production dump/object access, remote retention, key custody, rehearsal, restore.

## B8 — dependency bounds and compatibility-aware rollback

**Files**

- modify `pyproject.toml`, `uv.lock`
- create `deploy/release-metadata.schema.json`
- modify `scripts/deploy/lib.sh`, release/rollback scripts and tests
- document in `doc/deployment.md`

**Behavior**

Add `gunicorn>=23,<24` and validate the locked version. Each release contains `release-metadata.json`, validated against a JSON Schema with `additionalProperties: false`. Required fields and exact domains are: `schema_version` (integer `1`); `release_id` (string `YYYYMMDDTHHMMSSZ-<12 lowercase hex commit prefix>`); `commit` (40 lowercase hex); `created_at` (UTC RFC 3339 seconds, identical to the timestamp encoded in `release_id`); `python_version`, `django_version`, and `gunicorn_version` (PEP 440 strings); `migration_leaves` (sorted unique array of `[app_label, migration_name]` string pairs); `schema_sequence` (non-negative integer); `minimum_compatible_schema_sequence` (integer from `0` through `schema_sequence`); `migration_safety` (enum `no-schema-change`, `backward-compatible`, `forward-only`, `destructive`); `media_storage_mode` (enum `filesystem`, `s3`); and `static_manifest_sha256` (64 lowercase hex). It contains no secrets or endpoints.

Release order is the tuple `(created_at, commit)` in ascending lexical order after schema validation; duplicate tuples or a release ID inconsistent with that tuple are invalid. `schema_sequence` is monotonically non-decreasing in this order, increments by exactly one for a release that changes `migration_leaves`, and remains unchanged otherwise. A changed leaf set may not use `no-schema-change`. `minimum_compatible_schema_sequence` is the oldest sequence accepted by that release: `no-schema-change` preserves it, `backward-compatible` may preserve or raise it, and `forward-only`/`destructive` must set it to their own `schema_sequence`. These invariants are checked against the retained predecessor metadata during release creation; missing predecessor evidence fails closed.

Rollback validates current and target metadata, then reads the live DB migration leaves. The verdict is deterministic and evaluated in this order before symlink mutation:

| Condition | Verdict |
|---|---|
| metadata/schema/order invariant missing or invalid; unknown live leaf; live leaves differ from current metadata | `REFUSE_METADATA_OR_DB_UNKNOWN` |
| target is not older than current in release order | `REFUSE_NOT_ROLLBACK` |
| `media_storage_mode` differs | `REFUSE_STORAGE_MODE` |
| target `schema_sequence` is greater than live/current sequence | `REFUSE_TARGET_REQUIRES_NEWER_SCHEMA` |
| target `schema_sequence` is less than current `minimum_compatible_schema_sequence` | `REFUSE_SCHEMA_TOO_OLD` |
| current `migration_safety` is `forward-only` or `destructive` and target sequence is lower | `REFUSE_IRREVERSIBLE_BOUNDARY` |
| target and current sequence are equal but their migration leaves differ | `REFUSE_LEAF_MISMATCH` |
| all prior checks pass | `ALLOW_CODE_STATIC_ONLY` |

Only `ALLOW_CODE_STATIC_ONLY` may repoint the symlink. A refused verdict has no override inside this script: exceptional recovery requires a separately reviewed maintenance/restore plan. The script never reverses migrations or restores DB/media automatically, and no opaque token or secret is accepted in argv, env, metadata, or logs.

Backup-tool compatibility floors are specified and tested in B7 rather than deferred to operators.

**Dependencies**: none for the dependency bound/schema definition. Its deploy-script enforcement consumes B1's release layout; B7 later consumes the metadata compatibility fields.

**Offline gate**: schema validation; release-ID/order/sequence invariant fixtures; bounded dependency/lock assertion; one fixture for every verdict row; compatible fixture succeeds; every incompatible/missing fixture refuses before symlink mutation; no authorization material in captured argv/logs.

**Rollback**: this is the rollback boundary. Incompatible state requires forward-fix or separately approved maintenance/restore plan.

**Live-only**: approving and performing host rollback.

## B9 — safe static collection and cleanup

**Files**

- modify `config/settings.py`, `config/settings_production.py`
- create `blog/test_static_delivery.py`
- modify `.github/workflows/ci.yml`, release script, docs

**Behavior**

All tests collect into a unique temporary absolute `STATIC_ROOT`; cleanup is owned by the test temporary-directory fixture. Release collection targets the new final release's own absolute `staticfiles` directory after validating that the resolved path is `<validated-release>/staticfiles`, is not empty/root/source/current, and is not a symlink. No repository command uses cwd-sensitive `rm -rf staticfiles`.

Collection produces a manifest and representative hashed project, component, admin, and Unfold assets. With `DEBUG=False`, Django returns 404 for `/static/`; Nginx is the production owner.

**Dependencies**: B4 aliases and B1 release root. B9 provides the manifest/static tree consumed by B6; B9 does not depend on B6.

**Offline gate**: collectstatic to `tmp_path` exits 0; manifest/hash assertions; unsafe path matrix refuses before delete/write; fake release collection cannot touch source or previous release; `git status` shows no generated static artifacts.

**Rollback**: retain each release's static tree through the rollback window; switching `current` restores matching assets.

**Live-only**: host filesystem ownership and Nginx serving checks.

## Ordered implementation and review graph

1. Foundation: B3 production parsing/PostgreSQL, B4 settings aliases, and B8 dependency bounds plus metadata schema.
2. Runtime truth: B3 health/readiness.
3. Release/static boundary: B1, B8 deploy enforcement, B2, then the acyclic static chain B4 → B9 → B6 (B4 may already be complete from foundation).
4. Storage portability: B5 after B4.
5. Operations: B7 orchestrator after B8 metadata is stable.
6. Independent review checks every B1–B9 gate and permits at most one bounded repair plus fresh review.
7. Documentation/instructions synchronization and full offline integration gate.
8. Commit/push only under explicit user authorization.
9. Live staging remains separately blocked pending credentials/resources and owner approval.

Writers must not overlap on `config/settings_production.py`, `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, deploy libraries, or shared docs. One implementation owner integrates each shared contract; subsystem workers own isolated tests/artifacts.

## Integrated offline acceptance gate

All results must be observed, not inferred:

- `uv lock --check` exits 0.
- focused production settings, infra, static, storage, deploy, and backup tests pass.
- PostgreSQL CI applies migrations and proves readiness 200; bounded failure proves 503.
- `uv run python manage.py check` exits 0.
- dummy production `manage.py check --deploy` exits 0 with zero warnings and no external connection.
- temporary-root `collectstatic` exits 0 and manifest/hash assertions pass.
- final-path Gunicorn config execution exits 0.
- shell syntax/safety harnesses pass with zero host/network/service side effects and no canary leakage.
- `uv run pytest -q` passes.
- `git diff --check` passes.
- status/diff/untracked/secret/generated-artifact review contains only approved repository paths and no `.env`, DB, media, backup, evidence, venv, credentials, or generated static tree.

## Explicit non-claims

Passing the offline gate does not prove Timeweb compatibility, public TLS/DNS, real PostgreSQL latency/failure behavior, S3 IAM/ACL/CORS/Range/cache semantics, host permissions, systemd/Nginx installation, backup durability, restore RPO/RTO, reboot persistence, or production rollback. Those require a separately approved live staging gate.