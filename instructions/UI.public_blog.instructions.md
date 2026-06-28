---
applyTo: "blog/views.py,blog/session_interactions.py,templates/blog/**/*.html,blog/components/**/*.py,blog/components/**/*.html,static/css/style.css,static/js/**/*.js,blog/test_public*.py,blog/test_ui_feedback.py,blog/test_quality_gates.py,doc/public-ui.md"
name: "UI.PublicBlog"
description: "Use for public blog list/detail UI, Bootstrap/django-components styling, HTMX partials, search/filter/pagination, Cyrillic search, reactions, visual QA and screenshots."
---

# UI — Public blog

## SSR first

The public blog is SSR-first. HTMX is progressive enhancement, not the only navigation path.

- Pagination remains ordinary links.
- Search/filter URLs remain shareable query strings.
- HTMX partials return only the intended fragment.
- Full-page responses must work without JavaScript.
- Content-type filters (`?type=article|video|audio|podcast`) must preserve SSR and shareable URLs.

## Public visibility

All public list/detail querysets must filter `Post.status = published`.

## Search

When search behavior changes, test Cyrillic queries separately. SQLite `icontains` is ASCII-centric; the project uses Python `casefold` fallback for non-ASCII search.

## Cards

- Cards use `Post.description`, cover/placeholder, type badge, category and tag links. Do not leak raw Markdown, frontmatter or service blocks into cards.
- Cards and detail pages expose a copy-link control with an absolute detail URL; link sharing is universal, not tied to network-specific buttons.

## Detail page

Detail page includes header, badges, session reactions, optional media player, optional timecodes, rendered Markdown body, series navigation, reading progress and image lightbox. Avoid duplicate H1 in body.

## Reactions

Views and likes are anonymous session interactions backed by `SessionPostInteraction`; do not spread this state across ad-hoc session dict keys.

## Visual QA

For visible UI changes:

1. Run relevant tests.
2. Open affected pages in browser.
3. Check console errors.
4. Verify key states, not just one happy screenshot.
5. If sending screenshots to the user, send readable WebP crops and inspect them first.
