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
