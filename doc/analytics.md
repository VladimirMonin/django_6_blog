# Analytics

## Post View Tracking

Each post detail page view is tracked via `PostView` model:

- `post` — FK to Post
- `session_key` — anonymous session key
- `viewed_at` — timestamp
- `read_depth` — 0.0 to 1.0, how far the user scrolled

## Read-Depth Endpoint

Public, no API key required:

```
POST /api/v1/posts/<slug>/read-depth/
Content-Type: application/json

{"read_depth": 0.75}
```

Called by `static/js/read-depth-tracking.js` on scroll, page hide, and every 15 seconds. Values are clamped to [0.0, 1.0].

## Admin Dashboard

`PostView` and `AuditLog` are registered in Unfold admin:

- **PostView**: browse individual view events, filter by date
- **AuditLog**: append-only trail of API actions (publish, status change, delete)

## AuditLog Model

| Field | Description |
|---|---|
| `action` | published / updated / status_changed / deleted / restored |
| `post` | FK to Post (SET_NULL) |
| `post_title` / `post_slug` | Snapshot at time of action |
| `api_key` | FK to ApiKey (SET_NULL) |
| `api_key_name` | Snapshot |
| `detail` | JSON: old_status, new_status, source_id, etc. |
| `created_at` | Timestamp |

## Stats Endpoint

```
GET /api/v1/stats/
Authorization: Bearer <token>
```

Returns aggregate counts: by status, by content type, top 5 categories, total views/likes, featured count.