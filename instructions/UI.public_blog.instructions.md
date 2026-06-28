---
applyTo: "blog/views.py,blog/session_interactions.py,templates/blog/**/*.html,blog/components/**/*.py,blog/components/**/*.html,static/css/style.css,static/js/**/*.js,blog/test_public*.py,blog/test_ui_feedback.py,blog/test_quality_gates.py,doc/public-ui.md"
name: "UI.PublicBlog"
description: "Use for public blog list/detail UI, SSR-first navigation, HTMX partials, search/filter/pagination, Cyrillic search, related posts, breadcrumbs, TOC, series navigation, reactions, visual QA and screenshots."
---

# UI — Public blog

## SSR first

The public blog is SSR-first. HTMX is progressive enhancement, not the only navigation path.

- Pagination remains ordinary links.
- Search/filter URLs remain shareable query strings.
- HTMX partials return only the intended fragment.
- Full-page responses must work without JavaScript.
- Content-type filters (`?type=article|video|audio|podcast`) must preserve SSR and shareable URLs.
- Series landing pages and post detail pages must remain directly bookmarkable.

## Public visibility

All public list/detail querysets must filter both:

- `Post.status = published`
- `Post.deleted_at IS NULL`

Do not leak `draft`, `archived`, or soft-deleted posts into public list/detail views.

## Search

When search behavior changes, test Cyrillic queries separately. SQLite `icontains` is ASCII-centric; the project uses a Python `casefold` fallback for non-ASCII search.

## Cards

- Cards use `Post.description`, cover/placeholder, type badge, category and tag links. Do not leak raw Markdown, frontmatter or service blocks into cards.
- Cards and detail pages expose a copy-link control with an absolute detail URL; link sharing is universal, not tied to network-specific buttons.
- Card filtering must preserve the list as SSR output even when HTMX enhances the interaction.

## Detail page

Detail page includes:

- header, badges and author/meta
- breadcrumbs
- session reactions
- optional media player
- optional timecodes
- rendered Markdown body
- TOC for long posts
- related posts
- series navigation
- reading progress
- image lightbox
- read-depth tracking hook

Avoid duplicate H1 in body. Do not render duplicate primary media players below the body.

## Series and discovery

- `Series` is a first-class navigation surface, not a category alias in public UI.
- Series landing pages list ordered posts by `series_order`.
- Detail pages should expose `prev` / `next` / position for posts inside a series.
- Related posts are part of the public discovery layer and should be checked when changing detail-page layout.

## Reactions and telemetry

- Views and likes are anonymous session interactions backed by `SessionPostInteraction`; do not spread this state across ad-hoc session dict keys.
- Read-depth telemetry is separate and goes through `PostView` / `/api/v1/posts/<slug>/read-depth/`.

## Visual QA

For visible UI changes:

1. Run relevant tests.
2. Open affected pages in browser.
3. Check console errors.
4. Verify key states, not just one happy screenshot.
5. When the change affects detail pages, check breadcrumbs / TOC / media / progress / lightbox if present.
6. If sending screenshots to the user, send readable WebP crops and inspect them first.
