---
applyTo: "**"
name: "CORE.Project"
description: "Use for django_6_blog setup, dependencies, settings, database boundary, uv workflow, forbidden local artifacts, and project-wide hard rules."
---

# CORE — Project rules

## Environment

- Use `uv` only for Python environment and dependencies.
- Python is selected via `uv sync --python 3.12` or another explicit uv-managed version.
- Do not add Poetry, `poetry.lock`, `poetry-core`, system Python setup, or Docker unless the user explicitly asks for that slice.
- Base `config.settings` uses SQLite for local development and ordinary tests. `config.settings_production` is a separate fail-closed boundary: PostgreSQL only, `DJANGO_DEBUG=false`, explicit HTTPS origins/hosts, and S3 media only.
- Production examples contain placeholders only. Repository/offline work never authorizes real credentials, SSH, DNS/TLS, remote PostgreSQL/S3, service installation/reload, deployment, backup, restore, or production data mutation.

## Commands

```bash
uv sync --python 3.12
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8036
uv run python manage.py check
uv run pytest -q
git diff --check
```

## Never commit

- `.env`
- `.venv/`
- `.hermes/`
- `.serena/`
- `db.sqlite3`
- `media/posts/*`
- `tests/assets/*`
- `__pycache__/`
- `*.pyc`
- generated screenshots/test artifacts unless explicitly requested as documentation assets

## Public data rules

- Public routes expose only posts where `Post.status = published` and `deleted_at IS NULL`.
- Draft, archived and soft-deleted details return `404`.
- Slug-only public URLs are the project convention.
- `Post.description` is required for public cards.
- Site author is a Django-side default, not Obsidian/frontmatter content.

## Commit gate

Before commit, run the smallest relevant tests plus:

```bash
uv run python manage.py check
git diff --check
git diff --cached --check
```

Then follow `instructions/DOCS.git.instructions.md` for staged-path/secret scans, commit-message truth, and explicit commit/push authorization.
