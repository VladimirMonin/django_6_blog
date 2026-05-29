"""Import local Obsidian notes into blog posts for smoke tests/prototypes."""

from __future__ import annotations

import re
from pathlib import Path

from django.core.files import File

from blog.models import Post, PostMedia

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
OBSIDIAN_NOTE_LINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def import_obsidian_note_to_post(note_path: Path, assets_dir: Path | None = None) -> Post:
    """Create a Post and PostMedia rows from an Obsidian Markdown note.

    The importer is intentionally small: it is a local prototype/smoke path,
    not a full vault synchronizer. It uses YAML-like frontmatter only for
    simple scalar fields such as ``title`` and copies embedded local media from
    ``assets_dir`` into Django's configured media storage.
    """

    note_path = Path(note_path)
    assets_dir = Path(assets_dir) if assets_dir else note_path.parent
    raw_markdown = note_path.read_text(encoding="utf-8")
    metadata, markdown_body = split_frontmatter(raw_markdown)
    markdown_body = normalize_obsidian_note_links(markdown_body)

    title = metadata.get("title") or note_path.stem
    status = metadata.get("status", "done")

    post = Post.objects.create(
        title=title,
        content=markdown_body,
        is_published=status != "draft",
    )

    for filename in unique_obsidian_embeds(markdown_body):
        source_path = assets_dir / filename
        if not source_path.exists() or not source_path.is_file():
            continue
        with source_path.open("rb") as source_file:
            PostMedia.objects.create(post=post, file=File(source_file, name=source_path.name))

    # Re-render after media rows exist, so Obsidian embeds resolve to /media/ URLs.
    post.content = markdown_body
    post.save()
    return post


def split_frontmatter(markdown_text: str) -> tuple[dict[str, str], str]:
    """Return simple frontmatter key/value metadata and Markdown body."""

    match = FRONTMATTER_RE.match(markdown_text)
    if not match:
        return {}, markdown_text

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"\'')
        if value and not value.startswith(("[", "{", ">")):
            metadata[key.strip()] = value

    return metadata, markdown_text[match.end():]


def unique_obsidian_embeds(markdown_text: str) -> list[str]:
    """List embedded filenames in source order without duplicates."""

    seen = set()
    filenames = []
    for match in OBSIDIAN_EMBED_RE.finditer(markdown_text):
        filename = Path(match.group(1).strip()).name
        if filename not in seen:
            seen.add(filename)
            filenames.append(filename)
    return filenames


def normalize_obsidian_note_links(markdown_text: str) -> str:
    """Replace non-embedded Obsidian wikilinks with readable text."""

    def replace(match):
        target = match.group(1).strip()
        alias = match.group(2)
        return (alias or target).strip()

    return OBSIDIAN_NOTE_LINK_RE.sub(replace, markdown_text)
