# Infrastructure

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

Runs on push to `main` and on PRs:
- `uv sync --frozen`
- `uv run python manage.py check`
- `uv run pytest -q`

## Health Endpoint

Public, no API key required:

```
GET /api/v1/health/
```

Returns:
```json
{
  "status": "ok",
  "db": "ok",
  "post_count": 42,
  "version": "1.0"
}
```

## Backup

```bash
uv run python manage.py backup [--output FILE]
```

Dumps all posts as JSON to stdout (or file). Lists media files.

## Scheduled Publishing

```bash
uv run python manage.py publish_scheduled
```

Publishes draft posts whose `published_at` timestamp has arrived. Run via cron.

## Environment Variables

See `.env.example` for all supported variables:

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev key | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Comma-separated allowed hosts |

## Makefile

| Target | Action |
|---|---|
| `make setup` | `uv sync --python 3.12` |
| `make migrate` | `uv run python manage.py migrate` |
| `make run` | `uv run python manage.py runserver 127.0.0.1:8036` |
| `make test` | `uv run pytest -q` |
| `make check` | `uv run python manage.py check` |

## Structured Logging

API actions (publish, delete, status change) are logged via Python `logging` module with structured metadata to the `api.views` logger.