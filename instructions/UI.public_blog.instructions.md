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
- Search, category, tag and content-type filters must survive SSR/HTMX pagination,
  load-more and filter navigation through one `request.GET` / `QueryDict` contract.
  A filter change must drop stale `page` and `load_more` parameters.
- Series landing pages and post detail pages must remain directly bookmarkable.

## Public visibility

All public list/detail querysets must filter both:

- `Post.status = published`
- `Post.deleted_at IS NULL`

Do not leak `draft`, `archived`, or soft-deleted posts into public list/detail
views, tag visibility/counts, series navigation or reaction endpoints. A like
request for a non-public post returns `404` without changing counters or session
interaction history.

## Search

When search behavior changes, test Cyrillic queries separately. SQLite `icontains` is ASCII-centric; the project uses a Python `casefold` fallback for non-ASCII search.

## Cards

- Cards use `Post.description`, cover/placeholder, type badge, category and tag links. Do not leak raw Markdown, frontmatter or service blocks into cards.
- Cards and detail pages expose a copy-link control with an absolute detail URL; link sharing is universal, not tied to network-specific buttons.
- At viewports `<=576px`, card/detail bottom actions are a right-aligned pair of equal dark 44×44 icon-only controls: copy-link on the left and the directional navigation action on the right. They share the same non-pill shape, border, padding, shadow and vertical alignment; labels remain available through `aria-label` and return on desktop.
- In every mobile interaction state (hover, focus, active, copied and copy-error), the two action controls retain identical 44×44 geometry and vertical alignment. Mobile transitions may affect semantic colors and shadows, but not `transform` or `scale`; both controls expose a geometry-neutral focus-visible ring.
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
- one detail-only return-to-top anchor with an SSR `#post-start` fallback

Avoid duplicate H1 in body. Do not render duplicate primary media players below the body.

## Detail navigation controls

- At `<=576px`, breadcrumbs are a non-sticky, single 44px row that visually
  contains Home and the category. The full current title remains in the
  accessibility tree as `aria-current="page"`, and the row must not cause
  horizontal scrolling.
- Above 576px, breadcrumbs remain sticky immediately below the site header;
  Home, category and a truncated current title stay in one row while the
  in-article section trail remains functional.
- Return-to-top exists only on detail pages as one accessible 44×44 dark anchor
  with a white up arrow and no visible text. Without JavaScript it remains a
  normal right-aligned flow link to `#post-start`.
- JavaScript may progressively make this anchor fixed only after one viewport
  of scrolling. It must respect reduced motion, avoid the mobile browser safe
  area, hide while it geometrically intersects bottom actions or while a
  lightbox is active/closing, and return keyboard focus to the H1 after use.

## Callouts and rendered HTML

- A public Obsidian callout has separate `.callout-title` and `.callout-body`
  nodes; inline Markdown and nested rich Markdown belong to their respective
  title/body nodes.
- `+` and `-` callouts use native `details` / `summary`: `+` is open initially,
  `-` closed initially. The summary keeps its keyboard-accessible native
  behavior and a visible focus state. Non-folded callouts are semantic `aside`
  notes; ordinary blockquotes stay blockquotes.
- `body_html|safe` is protected by a final allowlist sanitizer. It removes
  executable tags, event attributes and unsafe URL schemes while preserving the
  supported Markdown, Mermaid, HTML5 audio/video body embeds and project
  component markup.

## Series and discovery

- `Series` is a first-class navigation surface, not a category alias in public UI.
- Series landing pages list ordered public posts by `series_order`.
- Detail pages should expose `prev` / `next` / position for public posts inside
  a series; soft-deleted members must not affect neighbors, position or total.
- Related posts are part of the public discovery layer and should be checked when changing detail-page layout.

## Navigation accessibility

- A page that renders breadcrumbs exposes exactly one semantic breadcrumb
  navigation for the current location.
- The navbar toggler has an accessible name plus `aria-controls` and
  `aria-expanded` state tied to the collapse target.
- Exactly the current paginator link uses `aria-current="page"`.
- Decorative navigation and paginator icons are hidden from assistive
  technology with `aria-hidden="true"`.

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
