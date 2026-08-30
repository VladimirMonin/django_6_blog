# Analytics

## Yandex Metrika

Every full SSR page rendered through `templates/base.html` loads Yandex Metrika
counter `111929557` near the start of `<head>`. JavaScript-disabled visits use
the matching `<noscript>` pixel at the start of `<body>`.

The counter enables Webvisor, click map, accurate bounce tracking and outbound
link tracking. HTMX fragment responses do not repeat the counter script; the
initial full-page load owns analytics initialization. `static/js/metrika-events.js`
also sends one manual `hit` after a successful HTMX history push, replacement or
restoration when the effective URL changes. URL fragments are ignored, repeated
URLs are deduplicated, and the previous URL is passed as `referer`; unavailable
or blocked `ym` never interrupts navigation.

Meaningful interaction goals are sent through the same central owner and use
only bounded, content-free parameters (`page_path` and `content_kind`):

- `post_like` / `post_unlike` — after a successful HTMX reaction swap;
- `share_copy` — only after copying the post link succeeds;
- `media_start` — once per audio/video element when playback starts;
- `read_50` / `read_90` — once each after the corresponding reading threshold.

Create goals with these exact names in Metrika before relying on conversion
reports. Missing or blocked `ym` never breaks the corresponding UI behavior.

Yandex Webmaster ownership is served from the versioned root route
`/yandex_5834a95c038b9599.html`. Keep the filename and verification body stable
while the site is registered in Webmaster.

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
Authorization: Bearer ***
```

Returns aggregate counts: by status, by content type, top 5 categories, total views/likes, featured count.