---
name: SEO meta tags, sitemap, feeds
canonical: doc/seo.md
---

# SEO.meta.instructions.md

## Зона ответственности

Sitemap, robots.txt, RSS/Atom фиды, Open Graph, Twitter Card, JSON-LD, canonical URLs.

## Файлы

| Файл | Назначение |
|---|---|
| `blog/sitemaps.py` | Классы `PostSitemap`, `StaticViewSitemap` |
| `blog/feeds.py` | `LatestPostsFeed` (RSS 2.0), `AtomLatestPostsFeed` |
| `blog/views.py::robots_txt` | robots.txt view |
| `config/urls.py` | URL маршруты: `/sitemap.xml`, `/robots.txt`, `/feed/rss/`, `/feed/atom/` |
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
6. Canonical URL = `request.build_absolute_uri`.
7. OG tags на detail перезаписывают дефолтные из `base.html` через `{% block social_meta %}`.
8. Feed alternate links указывают на `/feed/rss/` и `/feed/atom/`.
9. JSON-LD строится как Python-структура и сериализуется через
   `DjangoJSONEncoder`, а не собирается JSON-шаблоном вручную. Перед вставкой в
   `<script type="application/ld+json">` символы `<`, `>` и `&` экранируются,
   чтобы пользовательский текст не мог закрыть script-блок; результат обязан
   оставаться валидным JSON и round-trip сохранять Unicode, кавычки и слеши.
10. Social image URLs use `request.build_absolute_uri(storage_url)`: relative media URLs become absolute, while already absolute S3/CDN URLs remain unchanged and must never become `https://hosthttps://cdn/...`.
11. Local secure-host tests prove generated canonical/OG/Twitter/JSON-LD markup only. Telegram/VK preview readiness requires a separately approved live check against a public HTTPS URL reachable by those crawlers.

## Добавление новых статических страниц в sitemap

Добавить URL name в `StaticViewSitemap.items()` в `blog/sitemaps.py`.