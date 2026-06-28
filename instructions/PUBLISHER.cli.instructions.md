---
name: PUBLISHER.cli
version: 1
scope: publisher/
status: active
canonical: doc/cli.md#publisher-cli-publisher
last_updated: 2026-06-29
---

# Publisher CLI — Agent Workflow

## Responsibility

The `publisher/` package is a standalone CLI tool for agents to publish Markdown/Obsidian notes to the blog via the REST API. It has **zero Django dependency** — only Python standard library (`urllib`, `argparse`, `json`, `re`).

## Architecture

```text
publisher/
├── __init__.py      # version
├── __main__.py      # python -m publisher entry point
├── cli.py           # argparse CLI, --dry-run, env vars
├── parser.py        # Markdown/frontmatter/timecode parser
├── client.py        # urllib HTTP client, ApiError
└── test_publisher.py # parser unit + CLI dry-run + E2E live_server
```

## Data flow

1. Agent calls `python -m publisher publish note.md --url URL --key TOKEN`
2. `parser.py` reads the `.md` file, splits frontmatter, extracts timecodes
3. `cli.py` builds a JSON payload (or prints it with `--dry-run`)
4. `client.py` sends `POST /api/v1/posts/publish/` with Bearer auth
5. API verifies token, permission, expiry and rate limit
6. API creates or updates the `Post`, writes `AuditLog`, and the post becomes visible if `status=published`

## Frontmatter fields

| Field | Maps to | Notes |
|---|---|---|
| `title` | `Post.title` | Fallback: first H1, filename |
| `description` | `Post.description` | **Required** |
| `content_type` / `type` | `Post.content_type` | article/video/audio/podcast, Russian aliases supported |
| `media_url` | `Post.media_url` | External URL for player |
| `tags` | `Post.tags` | Comma-separated or `[a, b]` |
| `category` | `Post.category` | Humanized category name |
| `series` | `Post.series` | Humanized series name |
| `series_order` | `Post.series_order` | Integer order inside the series |
| `status` | `Post.status` | `published` (default), `draft`, `archived` |
| `source_id` | `Post.source_id` | Idempotent external key |
| `cover` | `PostMedia` | Only used by `import_obsidian_note`, **not** by publisher CLI |

## CLI overrides

All frontmatter fields can be overridden via CLI args (`--title`, `--description`, `--content-type`, `--media-url`, `--status`, `--slug`). CLI args take precedence.

## Env vars

- `BLOG_API_URL` — base URL (alternative to `--url`)
- `BLOG_API_KEY` — API token (alternative to `--key`)

## Testing

Tests are in `publisher/test_publisher.py`:

- parser unit tests
- CLI dry-run tests via subprocess
- E2E live_server tests: parser → HTTP POST → DB → public render

E2E should prove more than the API response:

- published article becomes visible on the list and detail page
- draft stays hidden publicly
- all supported content types behave correctly
- replace/idempotent behavior is real
- invalid or revoked key fails correctly

## Rules

1. **Zero Django dependency** in `publisher/` — only stdlib. The package must work without `DJANGO_SETTINGS_MODULE`.
2. **No external packages** — no `requests`, no `click`, no `rich`. Only `urllib`, `argparse`, `json`.
3. **Parser is a copy, not an import** — `publisher/parser.py` duplicates frontmatter/timecode parsing logic from Django-side import code to stay Django-free. Keep them in sync when parsing logic changes.
4. **CLI is JSON-only** — no local media upload boundary. Covers and embedded local files belong to `import_obsidian_note`, not to publisher CLI.
5. **`--dry-run` is safe** — it never sends anything to the API, just prints the parsed payload as JSON.
6. **Series and category are independent** — do not overload one field into the other in new behavior. Backward compatibility may still exist server-side for legacy frontmatter, but new docs and new behavior should treat them as separate concepts.
