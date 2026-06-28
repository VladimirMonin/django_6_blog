---
name: API.publish.instructions
description: "API endpoints, auth, token management, permissions, rate limits and agent publishing workflow"
zone: API
scope: api/
---

# API Instructions

## Architecture

- `api/` app — separate Django app, namespace `api`, all routes under `/api/v1/`.
- No DRF. Plain Django views + `JsonResponse`. Zero extra dependencies.
- `blog/urls.py` stays unnamespaced — blog routes are the public site root.
- API supports both agent-managed publishing and public telemetry endpoints.

## Authentication

- `ApiKey` model in `api/models.py` — token auto-generated via `secrets.token_urlsafe(32)`.
- `require_api_key(permission)` decorator in `api/decorators.py` — checks the Bearer token from the `Authorization` header and returns:
  - `401` on missing / invalid / revoked / expired key
  - `403` when the key exists but lacks the required permission
  - `429` when the per-key rate limit is exceeded
- API keys are managed via Django admin (`/admin/api/apikey/`), NOT hardcoded in code or settings.
- `ApiKey.verify(token)` returns the active, non-expired key or `None`, updates `last_used_at`.
- Revocation sets `is_active=False` and `revoked_at=now()`.
- Keys have:
  - `permissions` JSON field
  - `expires_at` optional expiration timestamp

## Permissions

| Permission | Endpoints |
|---|---|
| `read` | `GET /api/v1/posts/`, `GET /api/v1/posts/<slug>/` |
| `publish` | `POST /api/v1/posts/publish/`, `POST /api/v1/posts/bulk/` |
| `delete` | `DELETE /api/v1/posts/<slug>/` |
| `status` | `PATCH /api/v1/posts/<slug>/status/` |
| `stats` | `GET /api/v1/stats/` |

New keys currently default to the full permission set.

## Rate limiting

- Per-API-key in-memory rate limit.
- Current limit: **60 requests per 60 seconds** per token.
- Exceeding the limit returns:

```json
{"error": "Rate limit exceeded", "retry_after": 17}
```

## Endpoints

### Public endpoints (no API key)

- `GET /api/v1/health/` — health check: status, DB status, post count, app version.
- `POST /api/v1/posts/<slug>/read-depth/` — browser telemetry endpoint for read-depth tracking (`{"read_depth": 0.0..1.0}`). Only works for published, non-deleted posts.

### Agent endpoints

- `POST /api/v1/posts/publish/` — create or replace a post from JSON.
  - Required: `title`, `description`, `content`.
  - Optional: `content_type`, `media_url`, `timecodes`, `tags`, `category`, `series`, `series_order`, `status`, `slug`, `replace`, `source_id`.
  - Returns 201 with serialized post, 400 on validation error, 409 if slug exists without `replace=true`.
  - If `source_id` matches an existing active post, publish behaves idempotently and updates that logical post.

- `POST /api/v1/posts/bulk/` — publish multiple posts from `{"posts": [...]}`.
  - Returns per-item success/error entries.

- `GET /api/v1/posts/` — list posts for agents.
  - Filters: `status`, `content_type`, `category`, `search`, `page`, `per_page`, `sort`.
  - Valid `sort`: `created_at`, `-created_at`, `title`, `-title`, `view_count`, `-view_count`, `published_at`, `-published_at`.
  - Returns `results` and `pagination`.

- `GET /api/v1/posts/<slug>/` — full detail for one post.

- `PATCH /api/v1/posts/<slug>/status/` — switch status among `published`, `draft`, `archived`.

- `DELETE /api/v1/posts/<slug>/` — **soft delete** by slug.
  - Sets `deleted_at`
  - Switches status to `archived`
  - Keeps the row in DB for audit/history

- `GET /api/v1/stats/` — aggregate stats:
  - by status
  - by content type
  - top categories
  - total views
  - total likes
  - featured count

## Validation rules

- JSON in, JSON out. No multipart media upload yet.
- `serialize_post()` in `api/serializers.py` is the source of truth for JSON shape.
- Error responses: `{"error": "message"}` or `{"errors": ["msg1", "msg2"]}`.
- Timecodes are normalized from `{time, label}` to `{time, seconds, label}`.
- For `video`, `audio`, `podcast`, `media_url` is required.
- Timecodes must match the accepted clock formats (`M:SS`, `MM:SS`, `H:MM:SS`, `HH:MM:SS`).

## Audit and logging

- Mutating endpoints create `AuditLog` entries.
- API actions are also emitted through structured JSON logging on the `api.*` loggers.
- Log payloads include action-level metadata such as `action`, `post_slug`, `api_key` when available.

## Public visibility / deletion rules

- Public site views must only expose `Post.status = published` and `deleted_at IS NULL`.
- Drafts, archived posts and soft-deleted posts must not leak into list/detail pages.

## Testing

API changes are covered across:
- `api/test_api.py`
- `api/test_api_extended.py`
- `api/test_api_operational.py`

When changing API behavior:
1. Run focused API tests first.
2. Then run `uv run pytest -q`.
3. If public behavior changes, verify the post actually appears/disappears on the site, not just in JSON.
