# Документация Django 6 Blog

Это актуальная точка входа в документацию проекта. Документы верхнего уровня в `doc/` должны быть короткими и атомарными: один документ — одна зона смысла.

## Актуальные документы

- [`development.md`](development.md) — локальная разработка, проверки, dependency policy, что нельзя коммитить.
- [`kanban.md`](kanban.md) — Hermes Kanban workflow для проектных слайсов, карточек, зависимостей, dispatch boundary и финального commit/push gate.
- [`architecture.md`](architecture.md) — текущая архитектура Django-приложения, модели, services, templates, static assets.
- [`content-import.md`](content-import.md) — Markdown/Obsidian импорт, frontmatter, локальные ссылки, media bundle.
- [`media-content.md`](media-content.md) — `article`/`video`/`audio`/`podcast`, HTML5-плееры, cover, `timecodes`, локальный primary media через API package.
- [`public-ui.md`](public-ui.md) — публичная лента, карточки, detail page, HTMX, реакции, визуальные gates.
- [`api.md`](api.md) — API endpoints, auth, JSON/multipart publication, idempotency, storage и recovery.
- [`cli.md`](cli.md) — management commands и Publisher CLI для Markdown с локальными assets.
- [`seo.md`](seo.md) — sitemap, robots.txt, RSS/Atom, OG/Twitter, JSON-LD, canonical.
- [`navigation.md`](navigation.md) — related posts, breadcrumbs, TOC, series landing, content type filter.
- [`analytics.md`](analytics.md) — PostView tracking, read-depth, AuditLog, stats endpoint.
- [`infrastructure.md`](infrastructure.md) — CI, health/readiness, env vars, Makefile, logging и offline/live boundary.
- [`deployment.md`](deployment.md) — active GitHub Deployments API pull transport, exact-SHA adapter, production settings, systemd/Nginx and rollback boundaries.
- [`backup-restore.md`](backup-restore.md) — encrypted PostgreSQL/media backup, prune, rehearsal and break-glass restore.
- [`timeweb-deployment-preparation.md`](timeweb-deployment-preparation.md) — current Timeweb resources, secrets boundary, deployment sequence, TLS and operational diagnostics.
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
6. Если меняется порядок работы через Hermes Kanban, синхронизируй `doc/kanban.md`, `instructions/AGENT.kanban.instructions.md` и kanban-блок в `AGENTS.md`.
