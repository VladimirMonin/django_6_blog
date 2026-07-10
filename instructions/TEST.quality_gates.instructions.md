---
applyTo: "blog/test_*.py,api/test_*.py,tests/**/*.py,templates/**/*.html,static/**/*.js,static/**/*.css,doc/development.md"
name: "TEST.QualityGates"
description: "Use for test strategy, pytest selection, Django check, rendered-link smoke, browser QA, visual evidence, API operational gates, and pre-commit verification in django_6_blog."
---

# TEST — Quality gates

## Testing ladder

Use the smallest test set that covers the change first, then broaden only when needed.

Common gates:

```bash
uv run python manage.py check
uv run pytest -q
git diff --check
```

## Focused packs

- Public routes/UI: `blog/test_public_route_smoke.py`, `blog/test_public_blog.py`, `blog/test_ui_feedback.py`, `blog/test_navigation.py`, `blog/test_frontend_quality.py`.
- Import: `blog/test_obsidian_import.py`, `blog/test_importer_metadata_links.py`, `blog/test_collect_note_assets.py`.
- Media/timecodes: `blog/test_content_types_timecodes.py`.
- Rendered links and quality: `blog/test_rendered_links.py`, `blog/test_quality_gates.py`.
- Model/domain regressions: `blog/test_model_regressions.py`, `blog/test_content_strategy.py`, `blog/test_analytics.py`.
- API: `api/test_api.py`, `api/test_api_extended.py`, `api/test_api_operational.py`, `api/test_publish_package.py`, `api/test_remote_media_e2e.py`, `api/test_cleanup_publish_packages.py`.
- Infra/ops: `blog/test_infra.py`.

## API / operational evidence

When API behavior changes, verify more than status codes:

- permission failures (`401` / `403`)
- rate-limit behavior (`429`)
- list/detail visibility rules for soft-deleted and unpublished posts
- real DB side effects (AuditLog / PostView / counters) when applicable
- public site behavior when the API affects what should appear on the site
- for remote assets: real `live_server` HTTP through the stdlib Publisher CLI, storage existence/cleanup, `PostMedia`, single-player render, secure-host social URLs and idempotent replay
- Publisher auth compatibility: deterministic normal and leading-`-` API keys via `--key` and `BLOG_API_KEY`; missing `--key` value must still fail in argparse and no token may appear in stdout/stderr

## Browser/visual QA

Required when changing user-visible layout, JS interactions, player behavior, image bounds, Mermaid controls, HTMX behavior, timecode UI, progress bar, or lightbox behavior.

Check:

- page loads
- console errors
- expected elements count
- active/hover/focus state when relevant
- no duplicated primary media players
- screenshots are readable if delivered to user
- for progress/lightbox, verify behavior change, not just DOM presence

## Evidence standard

Do not report a gate as passed unless a command or browser check actually ran. If a heavy gate is skipped, say why.
