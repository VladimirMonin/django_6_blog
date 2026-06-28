# SEO и мета-теги

## Обзор

Блог включает полный SEO-набор: sitemap, robots.txt, RSS/Atom фиды, Open Graph, Twitter Card, JSON-LD, canonical URLs.

## Sitemap.xml

Автоматически генерируется из опубликованных постов и статических страниц.

- URL: `/sitemap.xml`
- Классы: `blog/sitemaps.py` — `PostSitemap` (priority 0.8, weekly), `StaticViewSitemap` (priority 0.5, daily)
- Только `status=published` посты попадают в sitemap
- `lastmod` = `updated_at` поста

## robots.txt

- URL: `/robots.txt`
- View: `blog.views.robots_txt`
- Разрешает весь сайт, запрещает `/admin/` и `/api/`
- Содержит ссылку на sitemap

## RSS и Atom фиды

- RSS 2.0: `/feed/rss/`
- Atom 1.0: `/feed/atom/`
- Классы: `blog/feeds.py` — `LatestPostsFeed`, `AtomLatestPostsFeed`
- 20 последних опубликованных постов
- Каждый item: title, link, description, pubdate, updatedate, author

## Open Graph и Twitter Card

На страницах постов:

```html
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:url" content="...">
<meta property="og:type" content="article">
<meta property="og:image" content="...">  <!-- при наличии обложки -->
<meta name="twitter:card" content="summary_large_image">
```

## JSON-LD (Structured Data)

На detail-страницах постов:

| content_type | JSON-LD @type |
|---|---|
| article | `Article` |
| video | `VideoObject` |
| audio | `AudioObject` |
| podcast | `AudioObject` |

Поля: `headline`, `description`, `url`, `datePublished`, `dateModified`, `author`, `contentUrl` (для медиа), `image` (при наличии обложки).

## Canonical URLs

Каждая detail-страница содержит:

```html
<link rel="canonical" href="{{ request.build_absolute_uri }}">
<link rel="alternate" type="application/rss+xml" href="/feed/rss/">
<link rel="alternate" type="application/atom+xml" href="/feed/atom/">
```

## Тесты

`blog/test_seo.py` — 22 теста:

- Sitemap: содержит опубликованные посты, исключает черновики, валидный XML
- robots.txt: content-type, directives, sitemap reference
- RSS/Atom: содержит посты, исключает черновики, корректные поля
- JSON-LD: Article/VideoObject/AudioObject/AudioObject по типам контента, валидный JSON
- OG/Twitter: meta tags на detail
- E2E: publisher CLI → API → DB → сайт → sitemap → RSS → social meta → JSON-LD