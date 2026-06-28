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
| `blog/test_seo.py` | 22 теста SEO |

## Правила

1. Sitemap содержит **только** опубликованные посты (`status=published`).
2. robots.txt запрещает `/admin/` и `/api/`, ссылается на sitemap.
3. RSS/Atom фиды — 20 последних опубликованных постов.
4. JSON-LD `@type` зависит от `content_type`: Article → `Article`, Video → `VideoObject`, Audio/Podcast → `AudioObject`.
5. `contentUrl` в JSON-LD содержит `player_media_url` напрямую (не prepend host — URL уже абсолютный для внешних медиа).
6. Canonical URL = `request.build_absolute_uri`.
7. OG tags на detail перезаписывают дефолтные из `base.html` через `{% block social_meta %}`.
8. Feed alternate links указывают на `/feed/rss/` и `/feed/atom/`.

## Добавление новых статических страниц в sitemap

Добавить URL name в `StaticViewSitemap.items()` в `blog/sitemaps.py`.