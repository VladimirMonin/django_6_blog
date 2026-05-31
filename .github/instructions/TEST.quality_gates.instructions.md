---
applyTo: "blog/test_*.py,tests/**/*.py,templates/**/*.html,static/**/*.js,static/**/*.css,doc/development.md"
name: "TEST.QualityGates"
description: "Use for test strategy, pytest selection, Django check, rendered-link smoke, browser QA, visual evidence, and pre-commit verification in django_6_blog."
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

- Public routes/UI: `blog/test_public_route_smoke.py`, `blog/test_public_blog.py`, `blog/test_ui_feedback.py`.
- Import: `blog/test_obsidian_import.py`, `blog/test_importer_metadata_links.py`, `blog/test_collect_note_assets.py`.
- Media/timecodes: `blog/test_content_types_timecodes.py`.
- Rendered links and quality: `blog/test_rendered_links.py`, `blog/test_quality_gates.py`.
- Model/domain regressions: `blog/test_model_regressions.py`, `blog/test_content_strategy.py`.

## Browser/visual QA

Required when changing user-visible layout, JS interactions, player behavior, image bounds, Mermaid controls, HTMX behavior or timecode UI.

Check:

- page loads;
- console errors;
- expected elements count;
- active/hover/focus state when relevant;
- no duplicated primary media players;
- screenshots are readable if delivered to user.

## Evidence standard

Do not report a gate as passed unless a command or browser check actually ran. If a heavy gate is skipped, say why.
