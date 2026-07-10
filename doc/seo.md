# SEO и мета-теги

## Обзор

Блог включает полный SEO-набор: sitemap, robots.txt, RSS/Atom фиды, Open Graph, Twitter Card, JSON-LD, canonical URLs.

## Sitemap.xml

Автоматически генерируется из опубликованных постов и статических страниц.

- URL: `/sitemap.xml`
- Классы: `blog/sitemaps.py` — `PostSitemap` (priority 0.8, weekly), `StaticViewSitemap` (priority 0.5, daily)
- Только `status=published` посты с `deleted_at IS NULL` попадают в sitemap
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
- 20 последних опубликованных постов с `deleted_at IS NULL`
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

`og:image`, `twitter:image` и JSON-LD `image` используют URL configured storage. Относительный `/media/...` превращается в абсолютный через текущий request host; уже абсолютный S3/CDN URL сохраняется как есть и не получает host второй раз.

## JSON-LD (Structured Data)

На detail-страницах постов:

| content_type | JSON-LD @type |
|---|---|
| article | `Article` |
| video | `VideoObject` |
| audio | `AudioObject` |
| podcast | `AudioObject` |

Поля: `headline`, `description`, `url`, `datePublished`, `dateModified`, `author`, `contentUrl` (для медиа), `image` (при наличии обложки).

Structured data собирается в Python как словарь и сериализуется
`DjangoJSONEncoder`. Перед вставкой в `application/ld+json` символы `<`, `>` и
`&` переводятся в JSON Unicode escapes: пользовательские title/description не
могут закрыть `<script>` через `</script>`, при этом валидный JSON сохраняет
Unicode, кавычки, обратные слеши и переводы строк без искажений.

## Canonical URLs

Каждая detail-страница содержит:

```html
<link rel="canonical" href="{{ request.build_absolute_uri }}">
<link rel="alternate" type="application/rss+xml" href="/feed/rss/">
<link rel="alternate" type="application/atom+xml" href="/feed/atom/">
```

## Тесты

`blog/test_seo.py` — регрессионный пакет SEO:

- Sitemap: содержит только опубликованные, не soft-deleted посты, валидный XML
- robots.txt: content-type, directives, sitemap reference
- RSS/Atom: содержит опубликованные, не soft-deleted посты, корректные поля
- JSON-LD: Article/VideoObject/AudioObject по типам контента, валидный и
  script-safe JSON, round-trip hostile text, абсолютные media/cover URL
- OG/Twitter: meta tags на detail
- E2E: publisher CLI → API → DB → сайт → sitemap → RSS → social meta → JSON-LD

## Offline и live preview boundary

`api/test_remote_media_e2e.py` через реальный `live_server` и production-like HTTPS host доказывает, что remote upload создаёт публичную страницу, canonical, OG/Twitter, JSON-LD, sitemap и robots с согласованными абсолютными URL. Это проверка нашего HTML-контракта, а не подтверждение внешнего crawler cache.

Фактический preview в Telegram/VK можно считать проверенным только отдельным live gate: публичный HTTPS URL должен быть доступен crawler-ам, storage/CDN assets — без авторизации, а платформа должна заново забрать страницу. Такой сетевой тест запускается только после явного разрешения; локальный `live_server` его не заменяет.
