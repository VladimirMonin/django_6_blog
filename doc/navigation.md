# Navigation

## Related Posts

On each post detail page, 3 related posts are shown:
- Same category or shared tags
- Excludes current post
- Only published, not soft-deleted
- Rendered as cards below the article

## Breadcrumbs

Bootstrap 5 breadcrumb on every detail page:
- Главная (home)
- Category (if post has one)
- Post title (current)

## Table of Contents

For posts with 3+ h2/h3 headings:
- Auto-generated from `content_html`
- Collapsible card before article content
- Links to heading IDs
- Hidden for short posts

## Series Landing Page

```
/series/<slug>/
```

Lists public posts in a series, ordered by `series_order`:
- Series name and description header
- Numbered list of posts with type badges
- Links to each post
- Only published, not soft-deleted posts participate in landing/detail series navigation
- Soft-deleted members do not affect previous/next links, position or total

## Content Type Filter

On the post list page:
- Tabs: All / Статья / Видео / Аудио / Подкаст
- URL param: `?type=video`
- Combines with search, category and tag filters
- Active `search`, `category`, `tag` and `type` survive SSR/HTMX pagination,
  load-more and filter links; changing a filter clears stale pagination state

## Accessibility semantics

- A page that renders breadcrumbs exposes exactly one navigation for its current location
- Navbar collapse toggle has an accessible name, state and controlled target
- Only the current paginator link has `aria-current="page"`
- Decorative navigation/paginator icons use `aria-hidden="true"`
