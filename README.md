# Django 6 Blog

Экспериментальный Django 6 блог: SSR + HTMX, Bootstrap 5, django-components, Markdown/Obsidian импорт, локальные медиа, видео/аудио/подкасты и сессионные реакции.

## Быстрый старт

Проект использует только `uv` как менеджер окружения и зависимостей.

```bash
uv sync --python 3.12
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8036
```

Если нужна другая версия Python, выбирай её через `uv`, например `uv sync --python 3.13`. Системный Python, Poetry, Postgres и Docker не нужны, пока это не станет отдельной задачей.

## Переменные окружения

Для локальной разработки можно скопировать пример:

```bash
cp .env.example .env
```

Настройки читаются из process environment:

- `DJANGO_SECRET_KEY` — секрет Django;
- `DJANGO_DEBUG` — `true` / `false`;
- `DJANGO_ALLOWED_HOSTS` — hosts через запятую.

Файл `.env`, локальная база `db.sqlite3`, `.venv/`, `media/posts/*`, `tests/assets/*`, `__pycache__/` и `*.pyc` не коммитятся.

## Проверки

```bash
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
```

## Документация

Точка входа в документацию проекта: [`doc/README.md`](doc/README.md).

Основные документы:

- [`doc/development.md`](doc/development.md) — локальная разработка, проверки, safety gate перед коммитом;
- [`doc/architecture.md`](doc/architecture.md) — текущая архитектура приложения и границы подсистем;
- [`doc/content-import.md`](doc/content-import.md) — импорт Markdown/Obsidian заметок и локальных медиа;
- [`doc/media-content.md`](doc/media-content.md) — типы записей, плееры, обложки и таймкоды;
- [`doc/public-ui.md`](doc/public-ui.md) — публичный UI, карточки, фильтры, HTMX и реакции;
- [`doc/cli.md`](doc/cli.md) — management commands и примеры запуска;
- [`doc/agent-workflow.md`](doc/agent-workflow.md) — как агентам работать с проектом и инструкциями.

Исторические планы и исследовательские материалы остаются в [`doc/plans/`](doc/plans/), [`doc/architecture/`](doc/architecture/) и [`doc/researches/`](doc/researches/). Они не заменяют актуальные документы верхнего уровня.

## Что реализовано

- Публичные записи только со статусом `published`; `draft` скрыт и отдаёт `404`.
- Slug-only маршруты записей без числовых ID.
- Категории, теги и tag map по опубликованным постам.
- Поиск по заголовку, Markdown-контенту, категории и тегам; кириллица дополнительно проверяется через Python `casefold` для SQLite.
- SEO-friendly пагинация обычными ссылками и HTMX-обновления для поиска/догрузки.
- Карточки используют обязательное `Post.description`, а не сырой Markdown excerpt.
- Markdown рендерится в HTML при сохранении, включая таблицы, code blocks, callouts, изображения и Mermaid pan/zoom.
- Obsidian/Markdown импорт поддерживает frontmatter, локальные медиа, обложки, wikilinks, Markdown images и dry link-check.
- Типы записей: `article`, `video`, `audio`, `podcast`.
- HTML5-плееры для видео/аудио/подкастов через `media_url` или импортированный локальный файл.
- Кликабельные таймкоды из Markdown-блока ```` ```timecodes ```` с промоткой плеера.
- Просмотры и лайки через anonymous Django sessions с централизованной историей `SessionPostInteraction`.
- Автор публичного сайта задаётся дефолтом проекта, а не хранится в Obsidian/frontmatter.

## Инструкции для агентов

Перед изменениями читай [`AGENTS.md`](AGENTS.md). Он маршрутизирует к атомарным инструкциям в [`.github/instructions/`](.github/instructions/). В инструкции попадают только фундаментальные правила проекта: архитектурные границы, safety gates, workflow и устойчивые контракты. Текущие планы, release notes и временные отчёты туда не добавляются.
