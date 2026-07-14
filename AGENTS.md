# AGENTS.md — Django 6 Blog · Master Instruction

> This file is the project router for coding agents. It is not a substitute for subsystem instructions.
> Before touching a subsystem, read every relevant `instructions/*.instructions.md` file.

## Project identity

`django_6_blog` — Django 6 SSR blog/content platform.

Core stack:

- Python `>=3.12`, `uv` only.
- Django `6.0.x`.
- SQLite for local development/tests; fail-closed PostgreSQL settings for production.
- Bootstrap 5, django-components, HTMX.
- Markdown/Obsidian import with local media.
- Public content types: `article`, `video`, `audio`, `podcast`.
- Agent API under `/api/v1/` with token auth, permissions, rate limits, and audit logging.
- Timeweb production uses a GitHub Deployments API pull transport: GitHub-hosted verification, a root-owned VPS poller, an exact-SHA checkout adapter, systemd/Gunicorn, Nginx/HTTPS, PostgreSQL and private S3.

## Commands

```bash
# Setup
uv sync --python 3.12
uv run python manage.py migrate

# Run local preview
uv run python manage.py runserver 127.0.0.1:8036

# Quality gate
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
```

Use smaller tests first when the change is narrow.

## Hard rules

1. Use `uv`; do not introduce Poetry, system Python setup, Docker or Postgres unless the user explicitly asks for that slice.
2. Do not commit `.env`, `.venv/`, `.hermes/`, `.serena/`, `db.sqlite3`, `media/posts/*`, `tests/assets/*`, `__pycache__/` or `*.pyc`.
3. Public views must expose only posts where `status = published` **and** `deleted_at IS NULL`; drafts, archived posts and soft-deleted posts must stay hidden and return `404` on detail URLs.
4. `Post.description` is the public card excerpt source. Do not fall back to raw Markdown excerpts in cards.
5. Author is a site default from Django settings/context, not Obsidian/frontmatter metadata.
6. Markdown rendered with `|safe` is a security boundary: escape embedded user source and keep local asset paths inside `assets_dir`.
7. Media posts must render exactly one primary audio/video player on detail pages.
8. UI changes need relevant tests and browser/visual QA when the user asks to see the result.
9. Commit and push only on explicit user request.
10. API changes must keep docs/instructions synchronized in the same slice; do not let `instructions/API.publish.instructions.md` drift from real endpoints.
11. Remote local-asset publishing uses the authenticated multipart package endpoint. Paths must stay inside `--assets-dir`, packages must be idempotent, and storage code must not require a local filesystem `.path`.
12. Treat API tokens as opaque secrets. Publisher CLI compatibility includes every valid `secrets.token_urlsafe(32)` value, including a token beginning with `-`; never print tokens in dry-run, errors, logs or test evidence.
13. Production preparation is offline by default: repository tests and examples do not authorize SSH, DNS/TLS, PostgreSQL/S3 access, systemd/Nginx installation, backup/restore, deployment, or use of real credentials.

## Instruction routing

`instructions/` contains atomic subsystem instructions. Read all matching files before editing that area.

| Area | Instruction |
|---|---|
| Project setup, dependencies, project-wide safety | `instructions/CORE.project.instructions.md` |
| Hermes Kanban board, card contract, dispatch boundary | `instructions/AGENT.kanban.instructions.md` |
| Markdown/Obsidian import, frontmatter, local media | `instructions/CONTENT.import.instructions.md` |
| Video/audio/podcast, player, cover, timecodes | `instructions/CONTENT.media.instructions.md` |
| Public list/detail UI, HTMX, reactions, visual QA | `instructions/UI.public_blog.instructions.md` |
| Tests, smoke gates, browser evidence | `instructions/TEST.quality_gates.instructions.md` |
| README, `doc/`, instructions style | `instructions/DOCS.documentation.instructions.md` |
| Git inspection, staging, commit messages, commit/push safety | `instructions/DOCS.git.instructions.md` |
| Python docstrings | `instructions/docstring_python_code.instructions.md` |
| API endpoints, auth, token management, permissions | `instructions/API.publish.instructions.md` |
| Publisher CLI, Markdown parser, agent workflow | `instructions/PUBLISHER.cli.instructions.md` |
| SEO, sitemap, feeds, meta tags, JSON-LD | `instructions/SEO.meta.instructions.md` |
| Compatibility entry through `instructions/` | `instructions/main_guide.instructions.md` |
| Navigation, related posts, TOC, series landing | `doc/navigation.md` |
| Analytics, PostView, read-depth, AuditLog | `doc/analytics.md` |
| Infrastructure, CI, health, env | `doc/infrastructure.md` |
| Active Timeweb pull deployment, exact-SHA checkout adapter, systemd/Nginx and rollback boundaries | `doc/deployment.md` |
| Encrypted backup, pruning and restore | `doc/backup-restore.md` |

If no instruction clearly matches, read `doc/README.md`, inspect the current code, then update instructions only if the discovered rule is fundamental.

## Documentation routing

- `README.md` — short human entry point.
- `doc/README.md` — current documentation catalog.
- `doc/development.md` — local development and safety gates.
- `doc/kanban.md` — Hermes Kanban board workflow for project slices.
- `doc/architecture.md` — current architecture.
- `doc/content-import.md` — content import.
- `doc/media-content.md` — media posts and timecodes.
- `doc/public-ui.md` — public UI and interactions.
- `doc/api.md` — API endpoints and auth.
- `doc/seo.md` — sitemap, feeds, canonical, social metadata and JSON-LD.
- `doc/cli.md` — management commands.
- `doc/navigation.md` — related posts, breadcrumbs, TOC, series landing.
- `doc/analytics.md` — view tracking, read-depth, audit log, stats.
- `doc/infrastructure.md` — CI, backup, health, env, Makefile, logging.
- `doc/agent-workflow.md` — instruction maintenance workflow.

Historical plans, research and architecture serials are references, not current operational rules.

## Kanban workflow

Project kanban work uses the dedicated Hermes board:

```text
slug: django-6-blog
default workdir: /home/v/code/django_6_blog
```

Use Kanban CLI/database as the source of truth. Browser dashboard and Telegram notifications are reporting layers only.

Before creating, dispatching, reviewing or closing kanban cards, read `instructions/AGENT.kanban.instructions.md` and `doc/kanban.md`. Cards must include exact files/instructions to read, a narrow task, measurable done conditions, and evidence gates. Creating cards does not imply autonomous dispatch; run dispatch only when the user expects workers to start.

## Git discipline

Before inspecting, staging, committing, or pushing, read `instructions/DOCS.git.instructions.md`. The staged diff is the source of truth; commit and push only on explicit user request.
