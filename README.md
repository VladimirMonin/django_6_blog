# Django 6 Blog

Экспериментальный блог на Django 6: SSR + HTMX, Bootstrap 5, django-components, Markdown и локальные медиа.

## Локальный запуск через uv

Проект использует только `uv` как менеджер окружения и зависимостей.

```bash
uv sync --python 3.12
uv run python manage.py migrate
uv run python manage.py runserver
```

Если нужна другая версия Python, выбираем её через `uv`, например `uv sync --python 3.12` — без системной установки Python.

## Переменные окружения

Для локальной разработки можно скопировать пример:

```bash
cp .env.example .env
```

Файл `.env` не коммитится. Приложение читает значения из process environment:

- `DJANGO_SECRET_KEY` — секрет Django для локального/production окружения.
- `DJANGO_DEBUG` — `true`/`false`.
- `DJANGO_ALLOWED_HOSTS` — список host через запятую.

Проект сейчас остаётся SQLite-only. `DATABASE_URL`, Postgres и Docker Compose не добавлены намеренно.

## Проверки

```bash
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
```

Подробные рабочие правила, smoke-gates и список того, что нельзя коммитить: [`doc/development.md`](doc/development.md).

## Публичный блог

Реализовано:

- статусы постов: `published` и `draft`;
- публично видны только опубликованные посты;
- категории;
- теги;
- поиск по заголовку, Markdown-контенту, категории и тегам;
- обычные SEO-friendly ссылки пагинации;
- HTMX-поиск и догрузка карточек без полной перезагрузки страницы;
- paginator остаётся обычной ссылочной навигацией для поисковых роботов.

## Импорт локальной Obsidian-статьи

Реальные заметки и медиа для локальной проверки держим в ignored-папке `tests/assets/`.

```bash
uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --slug lm-studio-lesson-01 \
  --replace
```
