"""Local media reference discovery for Markdown and Obsidian notes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
OBSIDIAN_NOTE_LINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class MediaReference:
    """Resolved local media reference from Markdown source."""

    source_name: str
    path: Path


@dataclass(frozen=True)
class MediaReferenceResult:
    """Collected local media references and unresolved local targets."""

    found: list[MediaReference]
    missing: list[str]


def collect_local_media_references(markdown_text: str, assets_dir: Path) -> MediaReferenceResult:
    """Collect local image/media references from Obsidian and standard Markdown syntax.

    Supports:
    - Obsidian embeds: ``![[cover.webp]]`` and ``![[cover|Alt]]``;
    - standard Markdown images: ``![Alt](cover.webp)`` and ``![Alt](./cover.webp)``;
    - lookup by filename or by stem, so ``![[cover]]`` can resolve ``cover.webp``.

    External URLs and absolute paths are ignored because they are not local assets to copy.
    """

    assets_dir = Path(assets_dir)
    index = build_asset_index(assets_dir)
    found: list[MediaReference] = []
    missing: list[str] = []
    seen_paths: set[Path] = set()

    for source_name in iter_local_media_targets(markdown_text):
        resolved = index.get(normalize_target(source_name))
        if resolved is None:
            missing.append(source_name)
            continue
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        found.append(MediaReference(source_name=source_name, path=resolved))

    return MediaReferenceResult(found=found, missing=missing)


def collect_broken_local_links(markdown_text: str, assets_dir: Path) -> list[str]:
    """Return unresolved local media and document links from Markdown/Obsidian source."""

    assets_dir = Path(assets_dir)
    index = build_asset_index(assets_dir)
    missing: list[str] = []
    seen: set[str] = set()

    for target in list(iter_local_media_targets(markdown_text)) + list(iter_local_document_targets(markdown_text)):
        normalized = normalize_target(target)
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized not in index:
            missing.append(target)

    return missing


def iter_local_media_targets(markdown_text: str):
    """Yield local media targets from source Markdown in source order."""

    matches = []
    for match in OBSIDIAN_EMBED_RE.finditer(markdown_text):
        matches.append((match.start(), clean_target(match.group(1))))
    for match in MARKDOWN_IMAGE_RE.finditer(markdown_text):
        raw_target = match.group(2).strip().strip("<>")
        if is_external_or_absolute(raw_target):
            continue
        target = clean_target(raw_target)
        matches.append((match.start(), target))

    seen_targets = set()
    for _position, target in sorted(matches, key=lambda item: item[0]):
        normalized = normalize_target(target)
        if normalized in seen_targets:
            continue
        seen_targets.add(normalized)
        yield target


def iter_local_document_targets(markdown_text: str):
    """Yield local non-image Markdown links and Obsidian wikilinks in source order."""

    matches = []
    for match in OBSIDIAN_NOTE_LINK_RE.finditer(markdown_text):
        matches.append((match.start(), clean_target(match.group(1))))
    for match in MARKDOWN_LINK_RE.finditer(markdown_text):
        raw_target = match.group(2).strip().strip("<>")
        if is_external_or_absolute(raw_target) or raw_target.startswith("#"):
            continue
        matches.append((match.start(), clean_target(raw_target)))

    seen_targets = set()
    for _position, target in sorted(matches, key=lambda item: item[0]):
        normalized = normalize_target(target)
        if normalized in seen_targets:
            continue
        seen_targets.add(normalized)
        yield target


def build_asset_index(assets_dir: Path) -> dict[str, Path]:
    """Build a case-insensitive lookup by file name and stem for assets_dir files."""

    index: dict[str, Path] = {}
    if not assets_dir.exists() or not assets_dir.is_dir():
        return index

    for path in sorted(assets_dir.iterdir()):
        if not path.is_file():
            continue
        for key in {path.name, path.stem}:
            index.setdefault(normalize_target(key), path)
    return index


def clean_target(target: str) -> str:
    """Normalize user-facing target text without turning it into an absolute path."""

    target = unquote(target.strip().strip("<>"))
    return PurePosixPath(target).name


def normalize_target(target: str) -> str:
    return clean_target(target).casefold()


def is_external_or_absolute(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme or parsed.netloc or target.startswith("/"))
