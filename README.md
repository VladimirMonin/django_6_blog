# Django 6 Blog

Экспериментальный блог на Django 6.

## Локальный запуск через uv

```bash
uv sync --python 3.12
uv run python manage.py migrate
uv run python manage.py runserver
```

## Проверки

```bash
uv run python manage.py check
uv run pytest
```

## Импорт локальной Obsidian-статьи

Реальные заметки и медиа для локальной проверки держим в ignored-папке `tests/assets/`.

```bash
uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --slug lm-studio-lesson-01 \
  --replace
```
