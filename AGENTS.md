# AGENTS.md — Django 6 Blog · Master Instruction

> This file is the project router for coding agents. It is not a substitute for subsystem instructions.
> Before touching a subsystem, read every relevant `instructions/*.instructions.md` file.

## Project identity

`django_6_blog` — Django 6 SSR blog/content platform.

Core stack:

- Python `>=3.12`, `uv` only.
- Django `6.0.x`.
- SQLite-only for the current project stage.
- Bootstrap 5, django-components, HTMX.
- Markdown/Obsidian import with local media.
- Public content types: `article`, `video`, `audio`, `podcast`.

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
2. Do not commit `.env`, `.venv/`, `db.sqlite3`, `media/posts/*`, `tests/assets/*`, `__pycache__/` or `*.pyc`.
3. Public views must expose only `Post.status = published`; drafts stay hidden and return `404` on detail URLs.
4. `Post.description` is the public card excerpt source. Do not fall back to raw Markdown excerpts in cards.
5. Author is a site default from Django settings/context, not Obsidian/frontmatter metadata.
6. Markdown rendered with `|safe` is a security boundary: escape embedded user source and keep local asset paths inside `assets_dir`.
7. Media posts must render exactly one primary audio/video player on detail pages.
8. UI changes need relevant tests and browser/visual QA when the user asks to see the result.
9. Commit and push only on explicit user request.

## Instruction routing

`instructions/` contains atomic subsystem instructions. Read all matching files before editing that area.

| Area | Instruction |
|---|---|
| Project setup, dependencies, commit safety | `instructions/CORE.project.instructions.md` |
| Markdown/Obsidian import, frontmatter, local media | `instructions/CONTENT.import.instructions.md` |
| Video/audio/podcast, player, cover, timecodes | `instructions/CONTENT.media.instructions.md` |
| Public list/detail UI, HTMX, reactions, visual QA | `instructions/UI.public_blog.instructions.md` |
| Tests, smoke gates, browser evidence | `instructions/TEST.quality_gates.instructions.md` |
| README, `doc/`, instructions style | `instructions/DOCS.documentation.instructions.md` |
| API endpoints, auth, token management | `instructions/API.publish.instructions.md` |
| Publisher CLI, Markdown parser, agent workflow | `instructions/PUBLISHER.cli.instructions.md` |

If no instruction clearly matches, read `doc/README.md`, inspect the current code, then update instructions only if the discovered rule is fundamental.

## Documentation routing

- `README.md` — short human entry point.
- `doc/README.md` — current documentation catalog.
- `doc/development.md` — local development and safety gates.
- `doc/architecture.md` — current architecture.
- `doc/content-import.md` — content import.
- `doc/media-content.md` — media posts and timecodes.
- `doc/public-ui.md` — public UI and interactions.
- `doc/api.md` — API endpoints and auth.
- `doc/cli.md` — management commands.
- `doc/agent-workflow.md` — instruction maintenance workflow.

Historical plans, research and architecture serials are references, not current operational rules.

## Git discipline

Before staging:

```bash
git status --short --branch
git diff --stat
git diff --cached --stat
git ls-files --others --exclude-standard
```

Before commit:

```bash
git diff --cached --check
git diff --cached --name-only | grep -E '(^\.env$|^\.venv/|^db\.sqlite3$|^media/posts/|^tests/assets/|__pycache__|\.pyc$)' && exit 1 || true
git diff --cached | grep -En '(AKIA|SECRET|TOKEN|PASSWORD|PASS|API[_-]?KEY|BEGIN RSA|BEGIN OPENSSH|ghp_|sk-|xoxb-|gsk_)' && exit 1 || true
```

Push only after the requested commit succeeds and the branch state is understood.
