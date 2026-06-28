---
name: API.publish.instructions
description: "API endpoints, auth, token management for agent-driven post publishing"
zone: API
scope: api/
---

# API Instructions

## Architecture

- `api/` app — separate Django app, namespace `api`, all routes under `/api/v1/`.
- No DRF. Plain Django views + `JsonResponse`. Zero extra dependencies.
- `blog/urls.py` stays unnamespaced — blog routes are the public site root.

## Authentication

- `ApiKey` model in `api/models.py` — token auto-generated via `secrets.token_urlsafe(32)`.
- `require_api_key` decorator in `api/decorators.py` — checks `Authorization: Bearer <token>`, returns 401 on invalid/missing/revoked.
- API keys are managed via Django admin (`/admin/api/apikey/`), NOT hardcoded in code or settings.
- `ApiKey.verify(token)` returns the active key or `None`, updates `last_used_at`.
- Revocation sets `is_active=False` and `revoked_at=now()`.

## Endpoints

- `POST /api/v1/posts/publish/` — create or replace a post from JSON.
  - Required: `title`, `description`, `content`.
  - Optional: `content_type`, `media_url`, `timecodes`, `tags`, `category`, `series`, `series_order`, `status`, `slug`, `replace`.
  - Returns 201 with serialized post, 400 on validation error, 409 if slug exists without `replace=true`.
- `GET /api/v1/posts/` — list posts for agents.
  - Filters: `status`, `content_type`, `category`, `search`, `page`, `per_page`.
  - Returns `results` and `pagination`.
- `GET /api/v1/posts/<slug>/` — full detail for one post.
- `PATCH /api/v1/posts/<slug>/status/` — switch `published`/`draft`.
- `DELETE /api/v1/posts/<slug>/` — delete by slug.

## Conventions

- JSON in, JSON out. No multipart yet (planned for media upload).
- `serialize_post()` in `api/serializers.py` — single source of truth for post JSON shape.
- Endpoints covered by `api/test_api.py` and `api/test_api_extended.py`.
- Error responses: `{"error": "message"}` or `{"errors": ["msg1", "msg2"]}`.
- Timecodes parsed from `{time, label}` to `{time, seconds, label}` via `_parse_time_to_seconds()`.

## Future endpoints / current scope

Currently implemented beyond publish:

- `GET /api/v1/posts/`
- `GET /api/v1/posts/<slug>/`
- `PATCH /api/v1/posts/<slug>/status/`
- `DELETE /api/v1/posts/<slug>/`

Still planned:

- `GET /api/v1/stats/`