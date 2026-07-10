---
applyTo: "blog/models.py,blog/content_import/timecodes.py,blog/management/commands/create_content_note.py,templates/blog/post_detail.html,static/js/timecodes.js,static/css/style.css,blog/test_content_types_timecodes.py,doc/media-content.md"
name: "CONTENT.Media"
description: "Use for article/video/audio/podcast content types, Post.media_url, PostMedia primary media, covers, HTML5 players, clickable timecodes, and player regression gates."
---

# CONTENT — Media posts and timecodes

## Content types

`Post.content_type` supports `article`, `video`, `audio`, `podcast`.

- `video` renders a video player.
- `audio` and `podcast` render an audio player.
- `article` renders no primary media player.

## Player source

`Post.player_media_url` chooses external `media_url` first, then imported primary `PostMedia` of the expected type.

Detail pages must render exactly one primary player for media posts. Imported local audio/video embeds that become the primary player must not remain as standalone body embeds.

The same rule applies to remote multipart publication: a local primary asset becomes `PostMedia`, `Post.media_url` stays empty, and its standalone Markdown embed is stripped. An external HTTP(S) `media_url` and a local primary asset are mutually exclusive.

## Cover

- Cover comes from frontmatter `cover` or the first image `PostMedia`.
- Cover path must stay inside `assets_dir`.
- Publisher CLI resolves the same local cover contract inside `--assets-dir` and uploads it with the `cover` role.
- Thumbnail generation must read with the Django storage file API, not `file.path`, so S3-compatible pathless storage works.
- No-cover media cards should use the project placeholder style.

## Timecodes

Timecodes come from a Markdown fenced block named `timecodes`.

- Parse to `Post.timecodes`.
- Remove the block from Markdown body.
- For `video`, `audio`, `podcast`, validate strictly before DB write.
- Valid formats: `MM:SS label` and `H:MM:SS label`.
- Clickable timecode buttons seek the media element to `data-seek-seconds`.

## UI style

Timecodes are a project component, not generic Bootstrap outline buttons. Preserve the card/pill/accent style and accessible focus state.

## Verification

```bash
uv run pytest blog/test_content_types_timecodes.py -q
uv run python manage.py check
git diff --check
```

For visual/player changes, use browser QA: video detail, podcast/audio detail, `currentTime` after click, player count, and readable WebP crops if requested.
