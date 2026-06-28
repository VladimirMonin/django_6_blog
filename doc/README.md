# Документация Django 6 Blog

Это актуальная точка входа в документацию проекта. Документы верхнего уровня в `doc/` должны быть короткими и атомарными: один документ — одна зона смысла.

## Актуальные документы

- [`development.md`](development.md) — локальная разработка, проверки, dependency policy, что нельзя коммитить.
- [`architecture.md`](architecture.md) — текущая архитектура Django-приложения, модели, services, templates, static assets.
- [`content-import.md`](content-import.md) — Markdown/Obsidian импорт, frontmatter, локальные ссылки, media bundle.
- [`media-content.md`](media-content.md) — `article`/`video`/`audio`/`podcast`, HTML5-плееры, cover, `timecodes`.
- [`public-ui.md`](public-ui.md) — публичная лента, карточки, detail page, HTMX, реакции, визуальные gates.
- [`api.md`](api.md) — API endpoints, auth, token management.
- [`cli.md`](cli.md) — management commands и рабочие CLI-сценарии.
- [`seo.md`](seo.md) — sitemap, robots.txt, RSS/Atom, OG/Twitter, JSON-LD, canonical.
- [`agent-workflow.md`](agent-workflow.md) — правила для агентов и поддержка `instructions/`.

## Исторические материалы

- [`plans/`](plans/) — планы фаз и подфаз. Это плановая документация, а не актуальный справочник по текущему коду.
- [`architecture/`](architecture/) — архитектурный сериал по этапам разработки. Часть ранних документов может отражать старый стек или старые решения.
- [`researches/`](researches/) — исследовательские отчёты и материалы. Использовать как reference, но не как источник текущих правил проекта.
- [`videos/`](videos/) — материалы для видео/анонсов/транскриптов.

## Правила поддержки

1. README в корне остаётся краткой входной точкой.
2. Актуальные справочники живут в `doc/*.md` и должны быть атомарными.
3. Большие исторические серии и планы не смешиваются с текущими operational docs.
4. Если меняется поведение CLI, импорта, публичного UI, медиа или тестовых gates — обновляй соответствующий документ в том же слайсе.
5. Фундаментальные правила для агентов обновляй в `AGENTS.md` и `instructions/*.instructions.md`, а не в длинных чатовых отчётах.
