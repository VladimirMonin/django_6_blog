---
applyTo: "blog/content_import/**/*.py,blog/management/commands/collect_note_assets.py,blog/management/commands/import_obsidian_note.py,blog/test_*import*.py,doc/content-import.md,doc/cli.md"
name: "CONTENT.Import"
description: "Use for Markdown/Obsidian import, collect_note_assets, import_obsidian_note, frontmatter, description metadata, slug creation, local media links, assets_dir safety, and test assets."
---

# CONTENT — Import rules

## Responsibilities

Content import logic lives in `blog/content_import/`. Management commands should stay thin wrappers around domain functions.

## Required metadata

- `description` is required for public cards.
- Import must fail before DB writes when required metadata is missing.
- Title priority: CLI `--title`, frontmatter `title`, first Markdown H1, filename.
- If the first H1 duplicates the chosen title, remove it from saved Markdown body.
- Do not store author in Obsidian/frontmatter; site author is configured by Django.

## Local media and links

- Support Obsidian embeds, Markdown images, wikilinks, note-relative paths and vault-relative paths.
- Resolve local files inside the declared `assets_dir` only.
- Path traversal outside `assets_dir` is an error.
- `--check-links` is the dry gate for local Markdown/Obsidian links.
- `tests/assets/` is local ignored smoke data and must not be committed.

## Media creation

- Create `PostMedia` rows for found local files.
- Keep original filename metadata.
- For media posts, strip only standalone primary audio/video embeds from Markdown body after creating media rows; image embeds stay in body.

## Verification

For import changes, run focused tests first:

```bash
uv run pytest blog/test_obsidian_import.py blog/test_importer_metadata_links.py blog/test_collect_note_assets.py -q
```

If the change touches media posts or timecodes, also run `blog/test_content_types_timecodes.py`.
