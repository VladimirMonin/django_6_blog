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

На главной, `/about/`, страницах серий и post detail используется один полный
набор без дубликатов:

```html
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:url" content="...">
<meta property="og:type" content="article">
<meta property="og:image" content="...">
<meta property="og:image:secure_url" content="...">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="...">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="...">
<meta name="twitter:image:alt" content="...">
```

`blog.seo.social_image_context()` — единый источник этого набора. Запасная
карточка — raster PNG `static/images/django-6-blog-social.png` размером
1200×630 с alt `Exception Blog — Владимир Монин`; она используется на главной,
`/about/`, сериях и detail без cover.
Detail с cover использует `cover_media.thumbnail_og_url`: это стабильный
same-origin `/content-media/<id>/og/`, который stream-читает JPEG derivative
через Django Storage API. Его `og:image:type=image/jpeg`. Выбранный URL и для
cover, и для fallback также попадает в JSON-LD detail как `image`.

`og:image`, `twitter:image` и JSON-LD `image` используют абсолютный URL через
текущий request. Для cover это same-origin stable route без query-параметров,
подписи или имени storage object; он доступен только когда media принадлежит
опубликованной и не удалённой записи. Карточка не требует авторизации; private
S3 URL остаётся внутренней деталью чтения. Static fallback получает текущий host
через `{% static %}`; production-раздачу static обеспечивает обычный
static-hosting слой, а локально её можно проверить через `runserver`.

## Favicon

Базовый шаблон объявляет PNG-иконки 16×16 и 32×32, ICO `sizes="any"` и
Apple touch icon 180×180 через `{% static %}`. Поэтому production с
`ManifestStaticFilesStorage` публикует в HTML hash-адреса файлов. Исходные
static assets также включают web-app PNG 192×192 и 512×512; `favicon.ico`
содержит 16×16, 32×32 и 48×48 варианты.

Для требования Яндекс Вебмастера стабильно доступен неавторизованный
`/favicon.ico`: Django выдаёт 200 `image/x-icon` независимо от `DEBUG` и
задаёт `Cache-Control: public, max-age=86400`. Корневой URL преднамеренно
остаётся короткоживущим, а HTML использует fingerprinted static URLs.

## JSON-LD (Structured Data)

Структурированные данные собираются в `blog/seo.py` как `@graph` на всех
основных публичных поверхностях:

- главная: `WebSite` и `Person`;
- `/about/`: `ProfilePage` и тот же `Person`;
- detail: `Article`/`VideoObject`/`AudioObject`, `WebSite`, `Person` и
  `BreadcrumbList`;
- серия: `CollectionPage` и `BreadcrumbList`.

На detail-страницах постов центральный объект графа имеет один из типов:

| content_type | JSON-LD @type |
|---|---|
| article | `Article` |
| video | `VideoObject` |
| audio | `AudioObject` |
| podcast | `AudioObject` |

Поля detail: `headline`, `description`, `url`, `mainEntityOfPage`,
`datePublished`, `dateModified`, `author`, `publisher`, `contentUrl` (для
медиа), `image` (выбранная social image: cover или fallback). Автор и publisher ссылаются на
канонический `Person` `/about/`; неподтверждённые профили, должности,
организации и `sameAs` не добавляются.

Structured data собирается в Python как словарь и сериализуется
`DjangoJSONEncoder`. Перед вставкой в `application/ld+json` символы `<`, `>` и
`&` переводятся в JSON Unicode escapes: пользовательские title/description не
могут закрыть `<script>` через `</script>`, при этом валидный JSON сохраняет
Unicode, кавычки, обратные слеши и переводы строк без искажений.

## Canonical URLs

Главная, `/about/`, detail и страницы серий содержат ровно один абсолютный
canonical без query-параметров. Его строит `blog.seo.canonical_url()` через
`request.build_absolute_uri(request.path)`, поэтому текущий HTTPS host
сохраняется, а фильтры, пагинация и метки не становятся отдельной копией.

Detail дополнительно содержит:

```html
<link rel="canonical" href="{{ canonical_url }}">
<link rel="alternate" type="application/rss+xml" href="/feed/rss/">
<link rel="alternate" type="application/atom+xml" href="/feed/atom/">
```

## Эксперимент llms.txt и Markdown

`/llms.txt` — динамический UTF-8 `text/plain` v2-указатель. Он перечисляет
только публичные основные страницы и не более 20 последних записей со статусом
`published` и `deleted_at IS NULL`; для каждой записи указаны canonical HTML и
Markdown URL с её публичным `description`. Полные Markdown-тела туда не
копируются. Это локально проверяемый эксперимент по обнаружению, а не гарантия
индексации, цитирования, трафика или обучения модели.

У каждой такой записи есть `/post/<slug>.md` с `text/markdown; charset=utf-8`.
Представление строится из единственного сохранённого публичного источника
`Post.content`, после коротких title/description/author/published/modified/
canonical метаданных. Оно не раскрывает `content_html`, `source_id`, скрытые
поля или исходный Obsidian frontmatter. Markdown response содержит HTTP
`Link: <canonical-html>; rel="canonical"`; HTML detail ссылается на него через
`rel="alternate" type="text/markdown"` и на `/llms.txt` через
`rel="describedby"`.

Оба discovery-ответа используют ETag и Last-Modified на основе состояния
публичных постов. Абсолютные URL всегда строятся из path без query текущего
request host. `llms-full.txt` намеренно отсутствует: он создал бы растущий
дубликат корпуса и риск расхождения.

## Локальное наблюдение за заявленными crawler-кандидатами

`blog.middleware.CrawlerObservationMiddleware` после готового ответа
классифицирует только известные User-Agent кандидатов OpenAI, Anthropic,
Perplexity, Google, Bing и Brave. Для кандидата логгер
`crawler_observation` через существующий JSON console handler пишет ровно одну
запись с `provider`, `purpose`, `remote_ip`, `method`, `path` без query,
`status`, `elapsed_ms`, `user_agent` и всегда
`verified_identity=false`.

Это локальное наблюдение, а не проверка crawler. Один User-Agent можно
подделать: middleware не делает DNS/IP-проверку и не предоставляет allowlist
или управляющее решение. В запись не попадают query string, cookies,
`Authorization` или body. Любая ошибка классификации или логирования
игнорируется, поэтому не меняет исходный HTTP-ответ.

## Тесты

`blog/test_seo.py` — регрессионный пакет SEO:

- Sitemap: содержит только опубликованные, не soft-deleted посты, валидный XML
- robots.txt: content-type, directives, sitemap reference
- RSS/Atom: содержит опубликованные, не soft-deleted посты, корректные поля
- JSON-LD: Article/VideoObject/AudioObject по типам контента, валидный и
  script-safe JSON, round-trip hostile text, абсолютные media/cover URL,
  `@graph`, связи author/publisher/about и BreadcrumbList
- Canonical: один path-only URL на home/about/detail/series для secure host и
  запросов с query
- Detail: видимые ссылки автора ведут на `/about/`; реальные `created_at` и
  `updated_at` присутствуют в `<time datetime>`
- OG/Twitter: полный de-duplicated набор image meta на home/about/series/detail,
  fallback PNG 1200×630, cover precedence, JSON-LD equality и crawler User-Agent SSR
- AI discovery: `blog/test_ai_discovery.py` проверяет Content-Type/Unicode,
  public-only 404, Markdown source, canonical `Link`, conditional GET,
  HTML relations, отсутствие `llms-full.txt` и sitemap consistency
- Crawler observation: `blog/test_crawler_observation.py` проверяет
  классификацию, молчание для обычного User-Agent, query-free/privacy-bounded
  поля, fail-open при ошибке логгера и public/admin response paths
- E2E: publisher CLI → API → DB → сайт → sitemap → RSS → social meta → JSON-LD

## Offline и live preview boundary

`api/test_remote_media_e2e.py` через реальный `live_server` и production-like HTTPS host доказывает, что remote upload создаёт публичную страницу, canonical, OG/Twitter, JSON-LD, sitemap и robots с согласованными абсолютными URL. Это проверка нашего HTML-контракта, а не подтверждение внешнего crawler cache.

Фактический preview в Telegram/VK можно считать проверенным только отдельным live gate: публичный HTTPS URL должен быть доступен crawler-ам, storage/CDN assets — без авторизации, а платформа должна заново забрать страницу. Такой сетевой тест запускается только после явного разрешения; локальный `live_server` его не заменяет.
