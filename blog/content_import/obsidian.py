"""Import local Obsidian/Markdown notes into blog posts."""

from __future__ import annotations

import re
from ast import literal_eval
from pathlib import Path

from django.core.files import File

from blog.content_import.frontmatter import split_frontmatter
from blog.content_import.media_links import collect_local_media_references
from blog.models import Category, Post, PostMedia, Tag

OBSIDIAN_NOTE_LINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def import_obsidian_note_to_post(
    note_path: Path,
    assets_dir: Path | None = None,
    slug: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> Post:
    """Create a Post and PostMedia rows from a local Markdown/Obsidian note."""

    note_path = Path(note_path)
    assets_dir = Path(assets_dir) if assets_dir else note_path.parent
    raw_markdown = note_path.read_text(encoding="utf-8")
    metadata, markdown_body = split_frontmatter(raw_markdown)
    description = description or required_metadata(metadata, "description")
    markdown_body = normalize_obsidian_note_links(markdown_body)

    title = title or metadata.get("title") or note_path.stem
    status = metadata.get("status", "done")

    category = category_from_metadata(metadata)
    tag_names = tags_from_metadata(metadata)

    post = Post.objects.create(
        title=title,
        description=description,
        slug=slug or "",
        content=markdown_body,
        status=Post.Status.DRAFT if status == "draft" else Post.Status.PUBLISHED,
        category=category,
    )

    if tag_names:
        post.tags.set(Tag.objects.get_or_create(name=tag_name)[0] for tag_name in tag_names)

    references = collect_local_media_references(markdown_body, assets_dir)
    for reference in references.found:
        with reference.path.open("rb") as source_file:
            PostMedia.objects.create(post=post, file=File(source_file, name=reference.path.name))

    # Re-render after media rows exist, so local Markdown/Obsidian embeds resolve to /media/ URLs.
    post.content = markdown_body
    post.save()
    return post


def required_metadata(metadata: dict[str, str], key: str) -> str:
    value = metadata.get(key, "").strip()
    if not value:
        raise ValueError(f"Required frontmatter field is missing: {key}")
    return value


def tags_from_metadata(metadata: dict[str, str]) -> list[str]:
    """Return human-readable tag names from simple Obsidian frontmatter."""

    raw_tags = metadata.get("tags", "")
    if not raw_tags:
        return []

    if raw_tags.startswith("["):
        try:
            parsed_tags = literal_eval(raw_tags)
        except (SyntaxError, ValueError):
            parsed_tags = []
    else:
        parsed_tags = [tag.strip() for tag in raw_tags.split(",")]

    names = []
    seen = set()
    for tag in parsed_tags:
        tag_name = humanize_taxonomy_name(str(tag).strip().lstrip("#"))
        if tag_name and tag_name.casefold() not in seen:
            seen.add(tag_name.casefold())
            names.append(tag_name)
    return names


def category_from_metadata(metadata: dict[str, str]) -> Category | None:
    """Create a category from the Obsidian series value, if present."""

    series = metadata.get("series", "").strip()
    if not series:
        return None
    name = humanize_taxonomy_name(series.removesuffix("-course"))
    if not name:
        return None
    return Category.objects.get_or_create(name=name)[0]


def humanize_taxonomy_name(value: str) -> str:
    """Convert frontmatter slugs such as 'lm-studio' to readable labels."""

    words = re.split(r"[-_/\s]+", value.strip())
    acronyms = {"ai", "api", "llm", "lm", "ui", "uv"}
    return " ".join(
        word.upper() if word.casefold() in acronyms else word.capitalize()
        for word in words
        if word
    )


def normalize_obsidian_note_links(markdown_text: str) -> str:
    """Replace non-embedded Obsidian wikilinks with readable text."""

    def replace(match):
        target = match.group(1).strip()
        alias = match.group(2)
        return (alias or target).strip()

    return OBSIDIAN_NOTE_LINK_RE.sub(replace, markdown_text)
