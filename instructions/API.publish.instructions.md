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
- `require_api_key` decorator in `api/decorators.py` — checks `Authorization: Bearer <... 401 on invalid/missing/revoked.
- API keys are managed via Django admin (`/admin/api/apikey/`), NOT hardcoded in code or settings.
- `ApiKey.verify(token)` returns the active key or `None`, updates `last_used_at`.
- Revocation sets `is_active=False` and `revoked_at=now()`.

## Endpoints

- `POST /api/v1/posts/publish/` — create or replace a post from JSON.
  - Required: `title`, `description`, `content`.
  - Optional: `content_type`, `media_url`, `timecodes`, `tags`, `category`, `status`, `slug`, `replace`.
  - Returns 201 with serialized post, 400 on validation error, 409 if slug exists without `replace=true`.

## Conventions

- JSON in, JSON out. No multipart yet (planned for media upload).
- `serialize_post()` in `api/serializers.py` — single source of truth for post JSON shape.
- All endpoints tested in `api/test_api.py`.
- Error responses: `{"error": "message"}` or `{"errors": ["msg1", "msg2"]}`.
- Timecodes parsed from `{time, label}` to `{time, seconds, label}` via `_parse_time_to_seconds()`.

## Future endpoints (documented in doc/api.md, not implemented)

- `GET /api/v1/posts/` — list/search/filter
- `GET /api/v1/posts/<slug>/` — detail
- `PATCH /api/v1/posts/<slug>/status/` — publish/unpublish
- `GET /api/v1/stats/` — visitor and post statistics
- `DELETE /api/v1/posts/<slug>/` — delete post