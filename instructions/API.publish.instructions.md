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
- Consumers must treat the token as an opaque secret. A valid `secrets.token_urlsafe(32)` value may begin with `-`; CLI parsing must preserve it rather than interpreting it as another option.
- `ApiKey.verify(token)` returns the active, non-expired key or `None`, updates `last_used_at`.
- Revocation sets `is_active=False` and `revoked_at=now()`.
- Keys have:
  - `permissions` JSON field
  - `expires_at` optional expiration timestamp

## Permissions

| Permission | Endpoints |
|---|---|
| `read` | `GET /api/v1/posts/`, `GET /api/v1/posts/<slug>/` |
| `publish` | `POST /api/v1/posts/publish/`, `POST /api/v1/posts/publish-package/`, `POST /api/v1/posts/bulk/` |
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

- `POST /api/v1/posts/publish-package/` — publish one post and local assets as authenticated `multipart/form-data`.
  - Requires the `publish` permission and a valid `Idempotency-Key` header (8–128 characters: letters, digits, `.`, `_`, `-`).
  - The `manifest` form field uses protocol version 1 and contains `post`, `assets`, and canonical `package_sha256`; every declared asset has one matching `asset_<id>` file part.
  - A new package returns `201`; an exact completed replay for the same API key and idempotency key returns the original response with `200`.
  - Reusing the key for a different package, or replaying a pending/failed package, returns `409`. Validation errors return `400`; unexpected finalization failures return a generic `500`.
  - The post stays draft until files, `PostMedia`, tags and audit state are finalized; only then is the requested `published` status applied.
  - Replacement removes old `PostMedia` rows transactionally. Old object deletion runs after commit as best-effort cleanup, so a storage cleanup outage does not roll back the accepted replacement.

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

## Package validation and limits

- JSON publish remains backward-compatible for posts without local assets. Multipart publish is used for local covers, body images and local primary audio/video.
- Default package limits (overridable through matching Django settings): manifest 256 KiB, Markdown content 2 MiB, 32 assets, 512 MiB total; images 20 MiB each, audio 200 MiB each, video 500 MiB each.
- Accepted files: JPEG, PNG, WebP, GIF, MP4, WebM, MP3, OGG/Opus, WAV, FLAC and M4A. Extension, declared MIME, byte signature, size and SHA-256 must agree.
- Logical source references must be relative and must not contain traversal or host paths. Undeclared file parts, duplicate normalized filenames, duplicate cover/primary roles and type-incompatible primary media are rejected.
- A media post must have exactly one external HTTP(S) `media_url` or one matching local primary asset. An article cannot have a primary player asset.
- Package files are written through the configured Django storage API under deterministic names; no local filesystem `.path` assumption is allowed.

## JSON validation rules

- `POST /posts/publish/` remains JSON in, JSON out.
- `serialize_post()` in `api/serializers.py` is the source of truth for JSON shape.
- Error responses: `{"error": "message"}` or `{"errors": ["msg1", "msg2"]}`.
- Timecodes are normalized from `{time, label}` to `{time, seconds, label}`.
- For `video`, `audio`, `podcast`, `media_url` is required.
- Timecodes must match the accepted clock formats (`M:SS`, `MM:SS`, `H:MM:SS`, `HH:MM:SS`).

## Audit and logging

- Mutating endpoints create `AuditLog` entries.
- API actions are also emitted through structured JSON logging on the `api.*` loggers.
- Log payloads include action-level metadata such as `action`, `post_slug`, `api_key` when available.

## Failure recovery

- Failed package finalization deletes newly owned files best-effort and records the ledger row as `failed`.
- `uv run python manage.py cleanup_publish_packages --dry-run` reports stale pending/failed package files; without `--dry-run`, it deletes only names recorded by those packages. Default age is 24 hours; override it with `--older-than-hours N`.
- Do not delete arbitrary storage prefixes as recovery. `PublishPackage.storage_names` is the ownership boundary.

## Public visibility / deletion rules

- Public site views must only expose `Post.status = published` and `deleted_at IS NULL`.
- Drafts, archived posts and soft-deleted posts must not leak into list/detail pages.

## Testing

API changes are covered across:
- `api/test_api.py`
- `api/test_api_extended.py`
- `api/test_api_operational.py`
- `api/test_publish_package.py`
- `api/test_remote_media_e2e.py`
- `api/test_cleanup_publish_packages.py`

When changing API behavior:
1. Run focused API tests first.
2. Then run `uv run pytest -q`.
3. If public behavior changes, verify the post actually appears/disappears on the site, not just in JSON.
