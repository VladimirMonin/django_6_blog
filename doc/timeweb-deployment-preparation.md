# Timeweb deployment preparation

Repository behavior and offline checks are documented in `doc/deployment.md`; backup and restore gates are documented in `doc/backup-restore.md`. This file covers only the missing inputs and future live Timeweb boundary.

## Resource decisions

- VPS: use SSH only for bootstrap; create a dedicated `deploy` account and stop using root for CI.
- Object Storage: keep the existing bucket private for the first staging deployment.
- Private media mode uses presigned URLs: `MEDIA_S3_SIGNED_URLS=true` and an empty `MEDIA_S3_CUSTOM_DOMAIN`.
- Do not make the bucket public merely to satisfy application startup. Public/CDN mode is a separate later choice after social-preview and cache testing.

## Local files to fill

Both files are ignored by Git:

```text
.env.production  # Django/PostgreSQL/S3 values copied later to the server
.env.deploy      # SSH/GitHub environment preparation
```

Tracked field references:

- `.env.production.example`
- `.env.deploy.example`
- `deploy/systemd/django-6-blog.env.example`

Never send populated files through Telegram or commit them.

## GitHub production environment

Create an environment named `production`. Prefer a required reviewer while deployment is being stabilized.

Add only these environment secrets:

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | Public VPS hostname or IPv4 |
| `DEPLOY_PORT` | SSH port, normally `22` |
| `DEPLOY_USER` | Dedicated `deploy` account |
| `DEPLOY_SSH_PRIVATE_KEY` | Private half of a deploy-only Ed25519 key |
| `DEPLOY_KNOWN_HOSTS` | Pinned host-key line verified during bootstrap |

Application secrets do **not** belong in GitHub. Store them on the VPS at:

```text
/etc/django-6-blog/django-6-blog.env
owner: root
group: django-blog
mode: 0640
```

## Release trigger

- Push/PR to `main`: `.github/workflows/ci.yml` only.
- Tag `v*`: `.github/workflows/deploy.yml` verifies the repository and deploys.
- `workflow_dispatch`: manual production deploy/retry.

The deploy workflow uploads a Git archive and calls the host-owned adapter:

```text
/usr/local/sbin/django-6-blog-deploy
```

The adapter must be installed and reviewed during server bootstrap. Until then, the workflow is expected to fail closed rather than execute arbitrary remote shell fragments.

Tracked adapter example: `deploy/host/django-6-blog-deploy`. Install that file as
`/usr/local/sbin/django-6-blog-deploy`, owned by `root:root`, mode `0755`, and
grant the deploy account only that fixed command. It accepts exactly a release
identifier and a 40-character commit, validates that they agree, reads the
matching uniquely named uncompressed Git archive from `incoming/`, and refreshes
a root-owned bare repository from its fixed `origin`. The commit must be reachable
from `origin/main` or be the target of a `v*` tag. The adapter creates its own
archive from that authorized commit and requires the uploaded bytes to match it
exactly before extraction. Git and Python verification run with clean
environments, so deploy-controlled `GIT_*`/`PYTHON*` variables cannot replace the
host provenance authority. A release that changes migration leaves therefore
fails closed until the adapter policy is deliberately reviewed; the workflow
does not carry an arbitrary shell fragment or application secrets.

The `deploy` account invokes only the following command through a narrow
passwordless sudoers rule:

```text
sudo -- /usr/local/sbin/django-6-blog-deploy <release-id> <commit>
```

It receives no general shell, package-manager or unrestricted systemctl
privilege.

The workflow validates host, user and port shapes before `scp`/`ssh`. The host
still validates release identity independently; GitHub-side checks are not the
security boundary.

Bootstrap also creates `/srv/django-6-blog/repository.git` as a root-owned bare
repository at mode `0700`, with a fixed trusted `origin`, and
`/srv/django-6-blog/.adapter-work` as `root:root 0711`. The adapter copies the
deploy-owned upload to a root-owned mode-`0600` file, opens it once, and checks
both its bytes and pathname identity against the host-generated archive. The
verified source remains root-owned and read-only; its release entry point is
executed through `runuser` as `deploy`, never as root.

## Offline executable gates

The repository-only gate now exercises these boundaries without contacting
Timeweb, S3 or GitHub:

- final-path release success, pre-cutover failure and readiness failure against
  an isolated release root, including a console-script shebang and execution
  bound to the final release virtualenv rather than the reviewer or an incoming
  path;
- source, previous-release and out-of-root sentinels plus unsafe release/static
  path refusal;
- backup tool versions for PostgreSQL 16/17/18 and bounded age/rclone/flock
  versions, malformed output, phase failures, lock refusal, `SUCCESS` and
  `last-success` publication order;
- prune dry-run, direct `/dev/tty` confirmation, exact count, selected backup
  and recomputed manifest digest;
- restore descriptor schema/mode/symlink/entry-point/TTY/marker/emptiness
  checks, restore-client/source-major matching and zero-target-write dry run;
- descriptor and production marker file descriptors remain open in the parent
  verifier and are the held authority revalidated after database/media emptiness
  checks and at the write boundary. Deterministic descriptor and production
  marker replacement is refused with zero database/media writes;
- fake-root host-adapter tests reject a forged commit archive and replacement of
  the private archive before any archive-provided release entry point can run.

These are offline safety proofs only. They do not prove host permissions,
systemd/Nginx installation, real PostgreSQL restore, S3 durability, network
identity, TLS, GitHub environment configuration or a successful live deploy.

## SSH bootstrap boundary

Use the Timeweb root password only for the initial interactive bootstrap. Do not save it in GitHub.

Bootstrap must:

1. Verify the server OS/version and SSH host fingerprint out of band.
2. Install the deploy public key.
3. Create `django-blog` system account and `deploy` operator account.
4. Restrict sudo for `deploy` to the reviewed adapter and required systemd operations only.
5. Install Python/uv, PostgreSQL client/server as chosen, Nginx, systemd units and the host adapter.
6. Create `/srv/django-6-blog/{incoming,releases}`, the root-owned `0711`
   `.adapter-work`, and the root-owned `0700` bare `repository.git` with its fixed
   trusted origin.
7. Create `/etc/django-6-blog/django-6-blog.env` from the populated local template.
8. Run an S3 upload/read/delete smoke before publishing content.
9. Validate Nginx/TLS, migrations, readiness and rollback before enabling tag deployment.

## Missing inputs before live bootstrap

- domain name for HTTPS and `DJANGO_ALLOWED_HOSTS`;
- server OS/version confirmation;
- decision whether PostgreSQL runs on this VPS or as a managed service;
- deploy public key;
- populated S3 access ID/material;
- final public author/site identity.
