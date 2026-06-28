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

Lists all posts in a series, ordered by `series_order`:
- Series name and description header
- Numbered list of posts with type badges
- Links to each post

## Content Type Filter

On the post list page:
- Tabs: All / Статья / Видео / Аудио / Подкаст
- URL param: `?type=video`
- Combines with search, category, tag filters