# Timeweb server bootstrap and first deployment plan

Status: approved orchestration plan; live execution remains gated.

## Goal

Bootstrap the existing Timeweb VPS for `django_6_blog`, deploy the reviewed application without Docker, and prove that PostgreSQL, private S3 media, Gunicorn, systemd, Nginx, TLS, backup, and rollback boundaries work without exposing credentials or losing SSH access.

## Ready result

- The repository-only production slice has passed an independent review, documentation sync, and the full local gate.
- The VPS has a dedicated `deploy` operator and `django-blog` service identity; root/password access is no longer used by CI.
- PostgreSQL is local-only and has a dedicated database and role.
- Application secrets live only in `/etc/django-6-blog/django-6-blog.env` with `root:django-blog` ownership and mode `0640`.
- Releases are installed below `/srv/django-6-blog/releases`, with `current` as the reviewed atomic symlink boundary.
- Gunicorn runs behind a Unix socket managed by systemd; Nginx owns static delivery and HTTPS termination.
- The existing private Timeweb S3 bucket passes an upload/read/delete smoke with signed URLs.
- GitHub Environment `production` contains only the reviewed SSH delivery inputs.
- A manual deployment succeeds and health, readiness, static, media, backup, restart, and code/static rollback checks have objective evidence.

## Input contract

The populated local source of truth is:

```text
/home/v/.config/django_6_blog/timeweb-bootstrap.toml
```

It remains outside Git, must stay a regular owner-only file with mode `0600`, and must never be copied into a card, plan, comment, log, command argument, or chat message. Evidence may report only section/key names, `set/missing/placeholder`, syntax validity, permission mode, and safe path-existence checks.

Derived local files may be generated from the validated TOML, but populated files remain ignored:

```text
.env.production
.env.deploy
```

## Canonical sequence

### Stage 0 — finish and accept the offline production slice

1. Let the existing serial implementation card finish its full tests and artifact/security scans.
2. Run the existing independent read-only review.
3. Synchronize durable docs and instruction routing.
4. Remove generated runtime artifacts and run the complete local gate.
5. Commit and push only under the already explicit Git boundary; no live action is implied by an offline PASS.

Exit evidence:

- focused and full tests pass;
- production `check --deploy`, shell syntax, workflow YAML, lock, diff, generated-artifact, ignored-file, and secret scans pass;
- independent review returns zero blockers;
- the pushed revision is the exact revision selected for the first deployment.

### Stage 1 — live authorization and identity canary

This stage starts only after the sticky `needs_input` gate records explicit authorization in redacted form.

1. Re-validate the bootstrap TOML without printing values.
2. Compare the expected SSH host fingerprint with an out-of-band value from the Timeweb console.
3. Perform one bounded SSH canary that reads only OS release, current user, hostname, disk availability, time synchronization, listening services, package-manager state, and current SSH configuration.
4. Record a sanitized inventory and stop if host identity, OS assumptions, storage, clock, or access differ from the plan.

No package installation, account mutation, firewall mutation, service restart, DNS change, or S3 write is allowed in this stage.

### Stage 2 — base host bootstrap

1. Capture rollback evidence for the current SSH and firewall configuration.
2. Apply security updates with a bounded maintenance window.
3. Create the `deploy` operator and `django-blog` system identity.
4. Install the deploy-only public key and prove a second concurrent key-based session before changing root/password access.
5. Install only the required host packages: PostgreSQL, Nginx, Python/uv prerequisites, Gunicorn runtime dependencies, backup tools, TLS tooling, and diagnostics.
6. Create reviewed directories under `/srv`, `/etc`, `/run`, and `/var/lib` with explicit ownership and modes.
7. Install the host-owned deploy adapter and constrained sudo policy; verify the deploy account cannot run arbitrary root commands.

Stop before disabling any access method unless two independent sessions and the rollback path are proven.

### Stage 3 — PostgreSQL, application environment, and private S3

1. Keep PostgreSQL bound to local interfaces only.
2. Create the dedicated role and database from the protected input contract without placing credentials in argv or logs.
3. Install `/etc/django-6-blog/django-6-blog.env` as `root:django-blog 0640`.
4. Verify production settings and migrations against the local PostgreSQL instance.
5. Run a bounded S3 upload/read/delete smoke against a unique temporary key and prove the bucket remains private.
6. Do not change bucket visibility, create a CDN/custom domain, or bulk-copy media in this stage.

### Stage 4 — application services and edge

1. Install reviewed systemd units, socket, backup timer, Gunicorn configuration, and Nginx configuration from the selected repository revision.
2. Run `systemd-analyze verify` where available and `nginx -t` before every reload.
3. Start the application behind the Unix socket and verify local liveness/readiness before exposing Nginx.
4. Configure the approved domain and TLS certificate.
5. Verify HTTP-to-HTTPS redirect, TLS chain, host handling, static cache classes, request-size boundary, and sanitized 503 behavior.
6. Keep HSTS disabled until HTTPS and rollback have passed from an external client.

DNS changes and certificate issuance are separate foreground operations with read-back; no blind batch mutation is allowed.

### Stage 5 — GitHub environment and first controlled deployment

1. Populate GitHub Environment `production` with only `DEPLOY_HOST`, `DEPLOY_PORT`, `DEPLOY_USER`, `DEPLOY_SSH_PRIVATE_KEY`, and `DEPLOY_KNOWN_HOSTS`.
2. Require the repository revision and GitHub Actions verification to be green.
3. Run the first deployment with `workflow_dispatch`, not a tag.
4. Verify the immutable release identifier, final-path virtualenv, migration policy, static manifest, current symlink, systemd state, and readiness.
5. Verify public article/media behavior without exposing signed URLs or credentials in evidence.

A successful canary does not yet authorize tag-driven production deployment.

### Stage 6 — operational acceptance

1. Reboot or restart services in a controlled order and verify persistence.
2. Run an encrypted backup and verify the remote `SUCCESS` contract and local sanitized evidence.
3. Perform code/static rollback only between compatible releases and prove readiness after rollback and forward deployment.
4. Prepare a disposable restore rehearsal as a separate explicitly authorized card. Never test production restore as part of ordinary deployment acceptance.
5. Check logs for credential leakage, repeated service restarts, Nginx errors, PostgreSQL failures, and failed S3 requests.
6. After all gates pass, authorize `v*` tag deployment and document the operator runbook.

## Kanban graph

```text
existing offline implementation
→ existing independent offline review
→ docs/instruction sync
→ final offline gate and Git closure
→ sticky live authorization gate
→ read-only SSH identity canary
→ base host bootstrap
→ PostgreSQL/env/private-S3 bootstrap
→ systemd/Gunicorn/Nginx/TLS integration
→ GitHub Environment + manual first deploy
→ live acceptance
→ separate needs-input disposable restore rehearsal
```

All repository writers remain serial in the shared checkout. Live cards are also serial because they mutate one host. Independent review cards are read-only. A rejected review does not authorize its successor; the coordinator must perform an explicit acceptance transition.

## We do not do

- No Docker or managed deployment platform.
- No public S3 bucket or CDN/custom-domain migration.
- No automatic deploy on every push to `main`.
- No secrets in GitHub beyond SSH delivery inputs.
- No password, private key, DSN, S3 material, or protected TOML value in Git, Kanban, chat, logs, argv, or evidence.
- No production restore, data deletion, backup pruning, DNS cutover, HSTS activation, or firewall lockout without a separate foreground authorization and rollback path.
- No unrelated application feature work or drive-by refactoring.

## Done when

- The exact deployed revision passed the offline review and full gate.
- Host identity and SSH rollback access were proven before mutations.
- PostgreSQL is local-only; production checks and migrations pass.
- Private S3 upload/read/delete and signed media behavior pass.
- systemd, Gunicorn, Nginx, TLS, health, readiness, static, and media checks pass.
- Manual GitHub deployment and compatible code/static rollback pass.
- Backup evidence exists and a separate disposable restore rehearsal is either passed or explicitly left blocked.
- Secrets remain absent from repository, card bodies/comments, logs, command arguments, and reports.

## Stop and ask Vladimir if

- SSH fingerprint, OS, package manager, domain authority, or target host differs from the validated input contract;
- the next operation can remove SSH access, mutate DNS, expose S3, delete data, prune backups, restore production, or incur a new paid resource;
- PostgreSQL/S3/TLS requires a new architecture rather than the documented host-local/private-bucket design;
- a second independent review requires another broad repair;
- Git history diverges or the deployment revision is not the reviewed pushed revision.
