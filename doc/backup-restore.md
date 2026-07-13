# Backup and restore

The repository provides an encrypted PostgreSQL + media backup contour and fail-closed restore entry points. This document does not authorize production access, backup upload, pruning, rehearsal or restore.

## Roles and objectives

- backup operator: timer monitoring, `last-success`, evidence retention and pruning;
- database operator: PostgreSQL source access and restore target verification;
- storage operator: media source/destination and object verification;
- security/key custodian: age key rotation, recovery and offline custody;
- Vladimir: change approver;
- restore commander: coordinates break-glass production restore.

Initial operational targets are RPO 24 hours and RTO 4 hours. Retention policy is 14 daily, 8 weekly and 12 monthly backups; pre-migration backups are retained for 30 days. These targets are not proven until a live disposable rehearsal records achieved values.

## Artifacts and host state

`deploy/systemd/django-6-blog-backup.service` invokes only `scripts/backup/run-backup.sh`; the daily timer never runs restore. Canonical host paths are:

```text
/var/lib/django-6-blog-backup/state
/var/lib/django-6-blog-backup/scratch
/var/lib/django-6-blog-backup/evidence
/run/lock/django-6-blog-backup.lock
/var/lib/django-6-blog-backup/state/last-success
/etc/django-6-blog/backup.env
```

The unit runs as `django-blog-backup`, declares writable state/lock paths and uses `ProtectSystem=strict`. Populate `/etc/django-6-blog/backup.env` out of band from the tracked example; keep it mode `0640`. PostgreSQL/rclone credentials and the age private identity are never committed.

Required environment:

| Variable | Purpose |
|---|---|
| `BACKUP_EXECUTION_MODE` | `live` requires the separate approval-file gate; tests use `fake` |
| `BACKUP_STATE_DIR`, `BACKUP_SCRATCH_DIR`, `BACKUP_EVIDENCE_DIR` | absolute host state paths |
| `BACKUP_LOCK_FILE` | absolute non-overlap lock path |
| `BACKUP_SOURCE_PG_MAJOR` | source PostgreSQL major: 16, 17 or 18 |
| `BACKUP_AGE_RECIPIENT` | public age recipient |
| `BACKUP_MEDIA_SOURCE` | rclone source alias/path |
| `BACKUP_MEDIA_DESTINATION` | separate off-server destination alias/path |
| `BACKUP_LIVE_APPROVAL_FILE` | live-only approval marker used by the execution-mode guard |

Restore additionally requires `RESTORE_AGE_IDENTITY_FILE`, `RESTORE_SCRATCH_DIR` and `BACKUP_MEDIA_DESTINATION`.

## Backup contract

`run-backup.sh` validates all variables and tools before creating state, obtains a non-blocking lock, then creates one `backup_id` containing:

- encrypted custom-format PostgreSQL archive;
- encrypted media archive/copy;
- closed manifest and SHA-256 checksums;
- sanitized local evidence;
- remote `SUCCESS` marker written last;
- atomic local `last-success` written only after remote success.

Supported tools are `pg_dump`/`pg_restore` major 16, 17 or 18 with equal source/client majors, `age >=1.2,<2`, `rclone >=1.68,<2`, and util-linux `flock >=2.39,<3`. Missing, malformed or unsupported versions fail before side effects.

## Verification and pruning

Offline tests use fake binaries and temporary directories:

```bash
uv run pytest -q tests/test_backup_script_safety.py
for file in scripts/backup/*.sh scripts/backup/lib/*.sh scripts/restore/*.sh; do bash -n "$file"; done
```

Pruning is dry-run by default:

```bash
scripts/backup/prune-backups.sh --dry-run
```

`--execute` is a future live operator action. It reads confirmation directly from `/dev/tty`, accepts exactly one listed backup, and recomputes candidate count and manifest digest before deletion. Never automate or timer-drive destructive prune.

## Restore descriptor and gates

Restore accepts only `--target-file ABSOLUTE_0600_JSON --backup-id ID`. The descriptor is a non-symlink file owned by the invoking uid with exactly:

- `schema_version: 1`;
- `target_kind: disposable|production`;
- normalized `target_id`, `database_name` and relative `media_prefix`;
- both `expected_database_empty` and `expected_media_empty` set to `true`;
- an absolute `maintenance_marker` below `/run/django-6-blog/restore-maintenance/`.

The verifier holds the opened descriptor as authority and revalidates identity after empty-target checks and at the write boundary. Production additionally requires a root-owned mode-`0600` maintenance marker containing the target id; that opened marker is revalidated at the same boundaries. Any replacement, stale marker, non-empty target, checksum/version mismatch or non-TTY execution refuses before database/media writes.

Entry points:

- `scripts/restore/rehearse-restore.sh` — disposable rehearsal;
- `scripts/restore/production-restore.sh` — production break-glass path;
- both delegate to `run-restore.sh`; do not call `execute-restore.sh` directly.

Restore confirmation is read from `/dev/tty`: `RESTORE DISPOSABLE <target_id> <backup_id>` or `RESTORE PRODUCTION <target_id> <backup_id>`. Restore is never part of deploy rollback and is never timer-driven.

## Monthly future rehearsal evidence

A separately approved disposable rehearsal must record, without secrets or row content:

1. encrypted archive checksum and `pg_restore --list` result;
2. migration/check/readiness outcomes and per-model row counts;
3. media object count, bytes, hashes and sampled download checks;
4. UTC start/end and achieved RPO/RTO;
5. sanitized logs and disposable-target cleanup proof.

Production restore remains blocked until the restore commander, Vladimir, database operator, storage operator and key custodian confirm the target, backup id, maintenance state and rollback implications.

## Non-claims

Offline tests do not prove production credentials, remote retention, off-server durability, age-key recoverability, PostgreSQL/S3 access, achieved RPO/RTO, systemd timer operation, monitoring alerts, prune safety against a real remote, or successful production restore.
