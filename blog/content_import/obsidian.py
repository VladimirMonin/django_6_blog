"""Import local Obsidian/Markdown notes into blog posts."""

from __future__ import annotations

import re
from ast import literal_eval
from pathlib import Path

from django.core.files import File

from blog.content_import.frontmatter import split_frontmatter
from blog.content_import.media_links import collect_local_media_references
from blog.content_import.timecodes import extract_timecode_blocks
from blog.models import Category, Post, PostMedia, Tag

OBSIDIAN_NOTE_LINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
LEADING_H1_RE = re.compile(r"\A\s*#\s+(.+?)\s*(?:\n+|\Z)")


def import_obsidian_note_to_post(
    note_path: Path,
    assets_dir: Path | None = None,
    slug: str | None = None,
    title: str | None = None,
    description: str | None = None,
    content_type: str | None = None,
    media_url: str | None = None,
) -> Post:
    """Create a Post and PostMedia rows from a local Markdown/Obsidian note."""

    note_path = Path(note_path)
    assets_dir = Path(assets_dir) if assets_dir else note_path.parent
    raw_markdown = note_path.read_text(encoding="utf-8")
    metadata, markdown_body = split_frontmatter(raw_markdown)
    description = description or required_metadata(metadata, "description")
    content_type = normalize_content_type(content_type or metadata.get("content_type") or metadata.get("type"))
    media_url = media_url or metadata.get("media_url", "").strip()
    markdown_body = normalize_obsidian_note_links(markdown_body)
    markdown_body, timecodes = extract_timecode_blocks(
        markdown_body,
        strict=content_type in {Post.ContentType.VIDEO, Post.ContentType.AUDIO, Post.ContentType.PODCAST},
    )

    title = title or metadata.get("title") or title_from_leading_h1(markdown_body) or note_path.stem
    markdown_body = remove_duplicate_leading_h1(markdown_body, title)
    status = metadata.get("status", "done")

    category = category_from_metadata(metadata)
    tag_names = tags_from_metadata(metadata)

    post = Post.objects.create(
        title=title,
        description=description,
        slug=slug or "",
        content=markdown_body,
        content_type=content_type,
        media_url=media_url,
        timecodes=timecodes,
        status=Post.Status.DRAFT if status == "draft" else Post.Status.PUBLISHED,
        category=category,
    )

    if tag_names:
        post.tags.set(Tag.objects.get_or_create(name=tag_name)[0] for tag_name in tag_names)

    cover_reference = resolve_cover_reference(metadata.get("cover", ""), assets_dir)
    if cover_reference:
        create_post_media(post, cover_reference)

    references = collect_local_media_references(markdown_body, assets_dir)
    existing_originals = set(post.media_files.values_list("original_filename", flat=True))
    for reference in references.found:
        if reference.path.name in existing_originals:
            continue
        create_post_media(post, reference.path)
        existing_originals.add(reference.path.name)

    # Re-render after media rows exist, so local Markdown/Obsidian embeds resolve to /media/ URLs.
    post.content = markdown_body
    post.save()
    return post


def create_post_media(post: Post, source_path: Path) -> PostMedia:
    """Attach a local media file to a post preserving original filename order."""

    with source_path.open("rb") as source_file:
        return PostMedia.objects.create(
            post=post,
            file=File(source_file, name=source_path.name),
            original_filename=source_path.name,
        )


def resolve_cover_reference(raw_cover: str, assets_dir: Path) -> Path | None:
    """Resolve frontmatter cover into a local asset path if present.

    Supports simple filenames/paths and Obsidian-style embeds such as
    ``![[cover.webp|600]]``. Missing covers are validated explicitly because a
    card cover is user-facing metadata, not optional prose.
    """

    cover = (raw_cover or "").strip().strip('"\'')
    if not cover:
        return None
    obsidian_match = re.fullmatch(r"!?\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", cover)
    if obsidian_match:
        cover = obsidian_match.group(1).strip()
    markdown_match = re.fullmatch(r"!?\[[^\]]*\]\(([^)]+)\)", cover)
    if markdown_match:
        cover = markdown_match.group(1).strip()
    assets_root = Path(assets_dir).resolve()
    cover_path = Path(cover)
    if not cover_path.is_absolute():
        cover_path = assets_root / cover_path
    cover_path = cover_path.resolve()
    try:
        cover_path.relative_to(assets_root)
    except ValueError as exc:
        raise ValueError("Cover path must stay inside assets_dir") from exc
    if cover_path.suffix.lower() not in PostMedia.IMAGE_EXTENSIONS:
        raise ValueError(f"Cover must be an image file: {cover}")
    if not cover_path.exists() or not cover_path.is_file():
        raise ValueError(f"Cover file not found: {cover}")
    return cover_path


def required_metadata(metadata: dict[str, str], key: str) -> str:
    value = metadata.get(key, "").strip()
    if not value:
        raise ValueError(f"Required frontmatter field is missing: {key}")
    return value


def normalize_content_type(value: str | None) -> str:
    """Normalize frontmatter/CLI content type to a Post.ContentType value."""
    normalized = str(value or Post.ContentType.ARTICLE).strip().casefold()
    aliases = {
        "article": Post.ContentType.ARTICLE,
        "post": Post.ContentType.ARTICLE,
        "lesson": Post.ContentType.ARTICLE,
        "note": Post.ContentType.ARTICLE,
        "статья": Post.ContentType.ARTICLE,
        "video": Post.ContentType.VIDEO,
        "видео": Post.ContentType.VIDEO,
        "audio": Post.ContentType.AUDIO,
        "аудио": Post.ContentType.AUDIO,
        "podcast": Post.ContentType.PODCAST,
        "подкаст": Post.ContentType.PODCAST,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        allowed = ", ".join(Post.ContentType.values)
        raise ValueError(f"Unsupported content type: {value!r}. Expected one of: {allowed}") from exc


def title_from_leading_h1(markdown_text: str) -> str:
    """Return the first Markdown H1 text when it starts the note body."""

    match = LEADING_H1_RE.match(markdown_text or "")
    if not match:
        return ""
    return match.group(1).strip()


def remove_duplicate_leading_h1(markdown_text: str, title: str) -> str:
    """Drop an initial H1 when it duplicates the post title rendered elsewhere."""

    match = LEADING_H1_RE.match(markdown_text or "")
    if not match:
        return markdown_text
    heading = match.group(1).strip()
    if heading.casefold() != (title or "").strip().casefold():
        return markdown_text
    return markdown_text[match.end() :].strip()


def tags_from_metadata(metadata: dict[str, str]) -> list[str]:
    """Return human-readable tag names from simple Obsidian frontmatter."""

    raw_tags = metadata.get("tags", "")
    if not raw_tags:
        return []

    if raw_tags.startswith("["):
        try:
            parsed_tags = literal_eval(raw_tags)
        except (SyntaxError, ValueError):
            parsed_tags = [tag.strip() for tag in raw_tags.strip("[]").split(",")]
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
