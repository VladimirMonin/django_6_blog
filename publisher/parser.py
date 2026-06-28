"""Parse Markdown/Obsidian notes into API-ready JSON payloads.

Reuses frontmatter and timecode parsers from ``blog.content_import`` when
running inside the Django project. When imported standalone (no Django
configured), falls back to a minimal local parser so the CLI works without
``DJANGO_SETTINGS_MODULE``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ── Frontmatter ────────────────────────────────────────────────────────────

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


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
        if value and not value.startswith(("{", ">")):
            metadata[key.strip()] = value

    return metadata, markdown_text[match.end():]


# ── Timecodes ──────────────────────────────────────────────────────────────

TIMECODE_FENCE_RE = re.compile(
    r"(?ms)^```timecodes\s*\n(?P<body>.*?)\n```\s*$"
)
TIMECODE_LINE_RE = re.compile(
    r"^\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s*(?:[-–—|:]\s*)?(?P<label>.+?)\s*$"
)


def time_to_seconds(time_text: str) -> int:
    """Convert MM:SS or H:MM:SS text into seconds."""
    parts = [int(part) for part in time_text.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def parse_timecodes(raw_text: str) -> list[dict[str, Any]]:
    """Parse a timecode block body into normalized entries."""
    entries: list[dict[str, Any]] = []
    for line in (raw_text or "").splitlines():
        if not line.strip():
            continue
        match = TIMECODE_LINE_RE.match(line)
        if not match:
            continue
        time_text = match.group("time")
        label = match.group("label").strip()
        if not label:
            continue
        entries.append({
            "time": time_text,
            "seconds": time_to_seconds(time_text),
            "label": label,
        })
    return entries


def extract_timecode_blocks(markdown_text: str) -> tuple[str, list[dict[str, Any]]]:
    """Remove ````timecodes` fences from Markdown and return parsed entries."""
    entries: list[dict[str, Any]] = []

    def replace(match: re.Match[str]) -> str:
        entries.extend(parse_timecodes(match.group("body")))
        return ""

    cleaned = TIMECODE_FENCE_RE.sub(replace, markdown_text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, entries


# ── Content type ───────────────────────────────────────────────────────────

CONTENT_TYPE_ALIASES = {
    "article": "article",
    "post": "article",
    "lesson": "article",
    "note": "article",
    "статья": "article",
    "video": "video",
    "видео": "video",
    "audio": "audio",
    "аудио": "audio",
    "podcast": "podcast",
    "подкаст": "podcast",
}


def normalize_content_type(value: str | None) -> str:
    """Normalize frontmatter/CLI content type to an API-accepted value."""
    normalized = str(value or "article").strip().casefold()
    return CONTENT_TYPE_ALIASES.get(normalized, "article")


# ── Title extraction ───────────────────────────────────────────────────────

LEADING_H1_RE = re.compile(r"\A\s*#\s+(.+?)\s*(?:\n+|\Z)")


def title_from_leading_h1(markdown_text: str) -> str:
    """Return the first Markdown H1 text when it starts the note body."""
    match = LEADING_H1_RE.match(markdown_text or "")
    return match.group(1).strip() if match else ""


def remove_duplicate_leading_h1(markdown_text: str, title: str) -> str:
    """Drop an initial H1 when it duplicates the post title."""
    match = LEADING_H1_RE.match(markdown_text or "")
    if not match:
        return markdown_text
    heading = match.group(1).strip()
    if heading.casefold() != (title or "").strip().casefold():
        return markdown_text
    return markdown_text[match.end():].strip()


# ── Obsidian wikilinks ─────────────────────────────────────────────────────

OBSIDIAN_NOTE_LINK_RE = re.compile(r"(?<!\!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def normalize_obsidian_note_links(markdown_text: str) -> str:
    """Replace non-embedded Obsidian wikilinks with readable text."""

    def replace(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        alias = match.group(2)
        return (alias or target).strip()

    return OBSIDIAN_NOTE_LINK_RE.sub(replace, markdown_text)


# ── Tags ───────────────────────────────────────────────────────────────────

def humanize_taxonomy_name(value: str) -> str:
    """Convert frontmatter slugs such as 'lm-studio' to readable labels."""
    words = re.split(r"[-_/\s]+", value.strip())
    acronyms = {"ai", "api", "llm", "lm", "ui", "uv", "e2e"}
    return " ".join(
        word.upper() if word.casefold() in acronyms else word.capitalize()
        for word in words
        if word
    )


def parse_tags(raw_tags: str) -> list[str]:
    """Parse frontmatter tags string into a list of human-readable names."""
    if not raw_tags:
        return []

    if raw_tags.startswith("["):
        try:
            from ast import literal_eval
            parsed = literal_eval(raw_tags)
        except (SyntaxError, ValueError):
            parsed = [tag.strip() for tag in raw_tags.strip("[]").split(",")]
    else:
        parsed = [tag.strip() for tag in raw_tags.split(",")]

    names: list[str] = []
    seen: set[str] = set()
    for tag in parsed:
        name = humanize_taxonomy_name(str(tag).strip().lstrip("#"))
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            names.append(name)
    return names


# ── Main parser ────────────────────────────────────────────────────────────

def parse_markdown_file(
    file_path: Path,
    *,
    title: str | None = None,
    description: str | None = None,
    content_type: str | None = None,
    media_url: str | None = None,
    status: str | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Parse a Markdown/Obsidian note into an API-ready JSON payload.

    Frontmatter fields take precedence unless overridden by CLI arguments:
        title, description, content_type/type, media_url, tags, series, status

    Timecode fences (```timecodes ... ```) are extracted and converted to
    structured entries with ``seconds`` for player seek.

    Returns a dict suitable for ``POST /api/v1/posts/publish/``.
    """
    file_path = Path(file_path)
    raw = file_path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(raw)

    body = normalize_obsidian_note_links(body)
    body, timecodes = extract_timecode_blocks(body)

    resolved_title = (
        title
        or metadata.get("title")
        or title_from_leading_h1(body)
        or file_path.stem
    )
    body = remove_duplicate_leading_h1(body, resolved_title)

    resolved_description = description or metadata.get("description", "").strip()
    if not resolved_description:
        raise ValueError(
            f"Required field 'description' is missing. "
            f"Add it to frontmatter or pass --description."
        )

    resolved_content_type = normalize_content_type(
        content_type or metadata.get("content_type") or metadata.get("type")
    )
    resolved_media_url = media_url or metadata.get("media_url", "").strip()
    resolved_status = status or metadata.get("status", "done")
    resolved_status = "draft" if resolved_status == "draft" else "published"

    tags = parse_tags(metadata.get("tags", ""))
    category = metadata.get("series", "").strip()
    category = humanize_taxonomy_name(category.removesuffix("-course")) if category else ""

    payload: dict[str, Any] = {
        "title": resolved_title,
        "description": resolved_description,
        "content": body,
        "content_type": resolved_content_type,
        "status": resolved_status,
    }
    if resolved_media_url:
        payload["media_url"] = resolved_media_url
    if timecodes:
        payload["timecodes"] = [
            {"time": tc["time"], "label": tc["label"]} for tc in timecodes
        ]
    if tags:
        payload["tags"] = tags
    if category:
        payload["category"] = category
    if slug:
        payload["slug"] = slug

    return payload