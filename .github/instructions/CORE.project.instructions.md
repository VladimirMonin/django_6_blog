---
applyTo: "README.md,pyproject.toml,uv.lock,.env.example,config/**/*.py,blog/**/*.py"
name: "CORE.Project"
description: "Use for django_6_blog setup, dependencies, settings, database boundary, uv workflow, commit safety, forbidden local artifacts, and project-wide hard rules."
---

# CORE — Project rules

## Environment

- Use `uv` only for Python environment and dependencies.
- Python is selected via `uv sync --python 3.12` or another explicit uv-managed version.
- Do not add Poetry, `poetry.lock`, `poetry-core`, system Python setup, Docker or Postgres unless the user explicitly asks for that slice.
- Current database boundary is SQLite. `DATABASE_URL`, Postgres and pgvector are separate future work.

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
- `db.sqlite3`
- `media/posts/*`
- `tests/assets/*`
- `__pycache__/`
- `*.pyc`
- generated screenshots/test artifacts unless explicitly requested as documentation assets

## Public data rules

- Public routes expose only `Post.status = published`.
- Draft details return `404`.
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

Then inspect staged paths and scan staged diff for secrets. Commit/push only after explicit user request.
