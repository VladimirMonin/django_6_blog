---
name: PUBLISHER.cli
version: 1
scope: publisher/
status: active
canonical: doc/cli.md#publisher-cli-publisher
last_updated: 2026-06-28
---

# Publisher CLI — Agent Workflow

## Responsibility

The `publisher/` package is a standalone CLI tool for agents to publish Markdown/Obsidian notes to the blog via the REST API. It has **zero Django dependency** — only Python standard library (`urllib`, `argparse`, `json`, `re`).

## Architecture

```
publisher/
├── __init__.py      # version
├── __main__.py      # python -m publisher entry point
├── cli.py           # argparse CLI, --dry-run, env vars
├── parser.py        # Markdown/frontmatter/timecode parser
├── client.py        # urllib HTTP client, ApiError
└── test_publisher.py # 42 tests (parser unit + CLI dry-run + E2E live_server)
```

## Data flow

1. Agent calls `python -m publisher publish note.md --url URL --key TOKEN`
2. `parser.py` reads the `.md` file, splits frontmatter, extracts timecodes
3. `cli.py` builds a JSON payload (or prints it with `--dry-run`)
4. `client.py` sends `POST /api/v1/posts/publish/` with Bearer auth
5. API creates the `Post` (see `instructions/API.publish.instructions.md`)
6. Post appears on the public site immediately if `status=published`

## Frontmatter fields

| Field | Maps to | Notes |
|---|---|---|
| `title` | Post.title | Fallback: first H1, filename |
| `description` | Post.description | **Required** |
| `content_type` / `type` | Post.content_type | article/video/audio/podcast, Russian aliases supported |
| `media_url` | Post.media_url | External URL for player |
| `tags` | Post.tags (M2M) | Comma-separated or `[a, b]` |
| `series` | Post.category (FK) | Kebab → humanized (lm-studio → LM Studio) |
| `status` | Post.status | `published` (default) or `draft` |
| `cover` | PostMedia | Only used by `import_obsidian_note` management command, NOT by publisher CLI |

## CLI overrides

All frontmatter fields can be overridden via CLI args (`--title`, `--description`, `--content-type`, `--media-url`, `--status`, `--slug`). CLI args take precedence.

## Env vars

- `BLOG_API_URL` — base URL (alternative to `--url`)
- `BLOG_API_KEY` — API token (alternative to `--key`)

## Testing

Tests are in `publisher/test_publisher.py`:

- **Parser unit tests** (20+): frontmatter, timecodes, content type, tags, title extraction, Obsidian wikilinks
- **CLI dry-run tests** (5): subprocess `python -m publisher publish ... --dry-run`, verify JSON output
- **E2E live_server tests** (7): full cycle via pytest-django `live_server` fixture — parser → HTTP POST → DB → public render

E2E tests cover:
- Article published → visible on list + detail
- Draft → hidden from public (404 on detail)
- Video with timecodes → seconds field correct
- All 4 content types (article/video/audio/podcast)
- Replace flag (409 without, 201 with)
- Invalid API key → 401
- Revoked key → 401

## Rules

1. **Zero Django dependency** in `publisher/` — only stdlib. The package must work without `DJANGO_SETTINGS_MODULE`.
2. **No external packages** — no `requests`, no `click`, no `rich`. Only `urllib`, `argparse`, `json`.
3. **Parser is a copy, not an import** — `publisher/parser.py` duplicates frontmatter/timecode parsing logic from `blog/content_import/` to stay Django-free. Keep them in sync when parsing logic changes.
4. **Timecodes are sent as `{time, label}`** — the API adds `seconds` server-side. The parser also computes `seconds` for dry-run output, but the API re-computes it.
5. **`--dry-run` is safe** — it never sends anything to the API, just prints the parsed payload as JSON.
6. **Cover images are NOT supported** — publisher CLI only sends JSON. Local file upload (covers, embedded media) requires the management command `import_obsidian_note`, not the API.