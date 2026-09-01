---
applyTo: "blog/seo.py,blog/discovery.py,blog/crawler_observation.py,blog/middleware.py,blog/context_processors.py,blog/sitemaps.py,blog/feeds.py,blog/views.py,config/urls.py,config/settings.py,templates/base.html,templates/blog/post_detail.html,templates/blog/about.html,templates/blog/series_detail.html,blog/components/post_card/post_card.html,blog/test_seo.py,blog/test_ai_discovery.py,blog/test_crawler_observation.py,doc/seo.md,doc/ai-discovery.md"
name: "SEO.Meta"
description: "Use for sitemap, robots.txt, RSS/Atom feeds, canonical URLs, Open Graph, Twitter Cards, JSON-LD, social image URLs, and SEO tests."
---

# SEO.meta.instructions.md

## Зона ответственности

Sitemap, robots.txt, RSS/Atom фиды, Open Graph, Twitter Card, JSON-LD, canonical URLs.

## Файлы

| Файл | Назначение |
|---|---|
| `blog/sitemaps.py` | Классы `PostSitemap`, `StaticViewSitemap` |
| `blog/feeds.py` | `LatestPostsFeed` (RSS 2.0), `AtomLatestPostsFeed` |
| `blog/discovery.py` | Experimental `/llms.txt` and public post Markdown representations |
| `blog/seo.py` | Canonical URL, shared schema.org entities and script-safe JSON-LD graphs |
| `blog/context_processors.py::seo_context` | Query-free canonical plus public WebSite/Person values for templates |
| `blog/views.py::robots_txt` | robots.txt view |
| `config/urls.py` | URL маршруты: `/sitemap.xml`, `/robots.txt`, feeds, `/llms.txt`, `/post/<slug>.md` |
| `templates/base.html` | OG/Twitter дефолтные теги, `extra_head` block |
| `templates/blog/post_detail.html` | OG/Twitter для поста, JSON-LD, canonical, alternate links |
| `config/settings.py` | `django.contrib.sitemaps` в INSTALLED_APPS |
| `blog/test_seo.py` | Регрессионный пакет SEO и JSON-LD |

## Правила

1. Sitemap содержит **только** опубликованные, не soft-deleted посты (`status=published`, `deleted_at IS NULL`).
2. robots.txt запрещает `/admin/` и `/api/`, ссылается на sitemap.
3. RSS/Atom фиды — 20 последних опубликованных, не soft-deleted постов.
4. JSON-LD `@type` зависит от `content_type`: Article → `Article`, Video → `VideoObject`, Audio/Podcast → `AudioObject`.
5. `contentUrl` в JSON-LD содержит `player_media_url` напрямую (не prepend host — URL уже абсолютный для внешних медиа).
6. `blog.seo.canonical_url()` строит canonical как `request.build_absolute_uri(request.path)`: он абсолютный, сохраняет реальный scheme/host и никогда не содержит query. Главная, `/about/`, detail и series имеют ровно один такой тег.
7. OG tags на detail перезаписывают дефолтные из `base.html` через `{% block social_meta %}`.
8. Feed alternate links указывают на `/feed/rss/` и `/feed/atom/`.
9. JSON-LD строится как Python-структура и сериализуется через
   `DjangoJSONEncoder`, а не собирается JSON-шаблоном вручную. Перед вставкой в
   `<script type="application/ld+json">` символы `<`, `>` и `&` экранируются,
   чтобы пользовательский текст не мог закрыть script-блок; результат обязан
   оставаться валидным JSON и round-trip сохранять Unicode, кавычки и слеши.
10. Social image URLs use `request.build_absolute_uri(storage_url)`: relative media URLs become absolute, while already absolute S3/CDN URLs remain unchanged and must never become `https://hosthttps://cdn/...`.
11. Local secure-host tests prove generated canonical/OG/Twitter/JSON-LD markup only. Telegram/VK preview readiness requires a separately approved live check against a public HTTPS URL reachable by those crawlers.
12. JSON-LD — это `@graph` из Python-структур: `WebSite` и `Person`; `ProfilePage` на `/about/`; `Article`/`VideoObject`/`AudioObject` и `BreadcrumbList` на detail. `author` и `publisher` detail указывают на тот же `Person`, чья `url` равна `/about/`. Не добавлять неподтверждённые `sameAs`, должности или организации.
13. Видимые авторские подписи карточек/detail/footer ведут на `/about/`. Detail показывает фактические `created_at` и `updated_at` через `<time datetime>`; schema использует те же значения.
14. `/llms.txt` — только компактный динамический UTF-8 `text/plain` v2-указатель на публичные основные страницы и не более 20 последних published/not-deleted постов. Это измеряемый эксперимент, не обещание индексации, цитирования, трафика или обучения. Не создавать `llms-full.txt` и не дублировать тела постов.
15. `/post/<slug>.md` принадлежит `blog.discovery`, отдаёт только published/not-deleted пост через UTF-8 `text/markdown`, включает title, description, site author, published/modified timestamps и query-free canonical HTML URL, а затем ровно сохранённый `Post.content`. Не добавлять `content_html`, `source_id`, скрытые поля или vault/frontmatter-источник. Response `Link` указывает только на canonical HTML; detail содержит `rel="alternate" type="text/markdown"` и `rel="describedby"` на `/llms.txt`.
16. Discovery responses получают ETag и Last-Modified из публичных постов; абсолютные ссылки строятся без query через текущий request host. Тесты проверяют Unicode, Content-Type, conditional GET, header safety, 404 hidden states и согласованность опубликованного URL с sitemap.
17. `CrawlerObservationMiddleware` наблюдает только заявленные User-Agent кандидатов OpenAI, Anthropic, Perplexity, Google, Bing и Brave после ответа. Он пишет ровно одну JSON-запись в логгер `crawler_observation` с provider, purpose, remote_ip, method, path без query, status, elapsed_ms, user_agent и неизменным `verified_identity=false`; он не пишет cookies, authorization, query или тело и не выполняет DNS/IP-проверку. Ошибка наблюдения не меняет HTTP-ответ; по одному User-Agent нельзя считать crawler подлинным.

## Добавление новых статических страниц в sitemap

Добавить URL name в `StaticViewSitemap.items()` в `blog/sitemaps.py`.