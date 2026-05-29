# Development guide

Рабочие правила проекта `django_6_blog`.

## Стек

- Python `>=3.12`, выбирается через `uv`.
- Django `6.0.x`; зависимость ограничена как `django>=6.0.5,<6.1`, чтобы не подтянуть будущие alpha/beta версии Django 6.1.
- SQLite — текущая рабочая база. PostgreSQL, `DATABASE_URL` и Docker Compose не используются, пока миграция на Postgres не станет отдельной задачей.
- `django-components` закреплён на `0.143.x`, потому что более новая ветка меняет поведение компонентов.
- `pytest` + `pytest-django` — основной тестовый запуск.

## Установка и запуск

```bash
uv sync --python 3.12
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8036
```

Если нужна другая версия Python, выбирай её через `uv`, например:

```bash
uv sync --python 3.13
```

Не нужно ставить Python через `apt`, `pyenv` или вручную, пока `uv` справляется сам.

## Локальные настройки

Пример локальных переменных лежит в `.env.example`.

```bash
cp .env.example .env
```

Файл `.env` игнорируется Git. Реальные секреты, локальная база `db.sqlite3`, `.venv/` и локальные медиа не должны попадать в коммиты.

Настройки читаются из process environment:

- `DJANGO_SECRET_KEY` — секрет Django.
- `DJANGO_DEBUG` — `true` / `false`.
- `DJANGO_ALLOWED_HOSTS` — hosts через запятую.

## Проверки перед коммитом

```bash
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
git status --short
```

Дополнительная проверка, что Poetry не вернулся:

```bash
git grep -nEi 'poetry|poetry-core' -- pyproject.toml README.md uv.lock || true
git ls-files | grep -E '(^|/)poetry\.lock$' && exit 1 || true
```

## Публичный блог

Публичная часть показывает только опубликованные посты:

- `Post.status = published` — виден в списке и детальной странице;
- `Post.status = draft` — скрыт и отдаёт `404` на детальной странице.

Поддерживаются:

- категории;
- теги;
- поиск по заголовку, Markdown-контенту, категории и тегам;
- SEO-friendly пагинация обычными ссылками;
- HTMX-частичные ответы для поиска и догрузки карточек;
- class-based views для списка, деталки, страницы «О блоге» и toggle-like endpoint;
- счётчик просмотров: один просмотр поста на одну anonymous session;
- лайки: один переключаемый лайк поста на одну anonymous session;
- централизованная история взаимодействий в `SessionPostInteraction`, чтобы позже расширить сессионные сценарии без разбрасывания логики по view.

Фильтры передаются query-string параметрами:

- `?search=...`
- `?category=slug`
- `?tag=slug`
- `?page=2`

## Импорт Obsidian-заметки

Для проверки реального Markdown и медиа используются ignored test assets в `tests/assets/`.

```bash
uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --slug lm-studio-lesson-01 \
  --replace
```

Команда:

- читает Markdown-файл;
- берёт `title` из frontmatter или имя файла;
- копирует найденные медиа в `media/posts/<post-slug>/`;
- создаёт/заменяет пост при `--replace`;
- конвертирует Markdown в HTML при сохранении `Post`.

## Что не коммитить

Перед `git add` проверяй, что в staged-файлы не попали:

- `.env`;
- `.venv/`;
- `db.sqlite3`;
- `media/posts/*` и другие локальные загрузки;
- `tests/assets/*` с локальными исходниками для smoke-проверок;
- `__pycache__/` и `*.pyc`.
