"""Collect note-local media into a flat assets directory."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from blog.content_import.frontmatter import split_frontmatter
from blog.content_import.media_links import is_external_or_absolute, iter_local_document_targets

OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


@dataclass(frozen=True)
class BundleItem:
    """A copied media file and its original Markdown target."""

    source_name: str
    source_path: Path
    copied_path: Path


@dataclass(frozen=True)
class BundleResult:
    """Result of copying a note and its media into one folder."""

    note_path: Path | None
    assets_dir: Path
    copied: list[BundleItem]
    missing: list[str]


def collect_note_media_bundle(
    note_path: Path,
    output_dir: Path,
    *,
    vault_root: Path | None = None,
    copy_note: bool = True,
    clean: bool = False,
    title: str | None = None,
    description: str | None = None,
) -> BundleResult:
    """Copy all local image/media references from a note into ``output_dir``.

    Supports Obsidian embeds such as ``![[999_files/img.webp|500]]`` and standard
    Markdown images such as ``![Alt](../media/img.webp)``. The output directory is
    intentionally flat so it can be passed to ``import_obsidian_note --assets-dir``.
    """

    note_path = Path(note_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not note_path.exists() or not note_path.is_file():
        raise FileNotFoundError(f"Note file not found: {note_path}")
    if note_path.suffix.lower() != ".md":
        raise ValueError(f"Expected a Markdown file: {note_path}")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_text = note_path.read_text(encoding="utf-8")
    _metadata, markdown_body = split_frontmatter(markdown_text)
    copied: list[BundleItem] = []
    missing: list[str] = []
    used_names: set[str] = set()
    copied_sources: set[Path] = set()

    targets = list(iter_media_targets_for_bundle(markdown_body)) + list(
        iter_local_document_targets(markdown_body)
    )
    for target in targets:
        source_path = resolve_media_target(target, note_path=note_path, vault_root=vault_root)
        if source_path is None:
            missing.append(target)
            continue
        if source_path in copied_sources:
            continue
        copied_sources.add(source_path)
        copied_path = output_dir / unique_filename(source_path.name, used_names)
        shutil.copy2(source_path, copied_path)
        copied.append(BundleItem(source_name=target, source_path=source_path, copied_path=copied_path))

    bundled_note_path = None
    if copy_note:
        note_text = markdown_text
        if title is not None or description is not None:
            note_text = upsert_frontmatter_fields(note_text, title=title, description=description)
        bundled_note_path = output_dir / note_path.name
        bundled_note_path.write_text(note_text, encoding="utf-8")

    return BundleResult(note_path=bundled_note_path, assets_dir=output_dir, copied=copied, missing=missing)


def iter_media_targets_for_bundle(markdown_text: str):
    """Yield local media targets with relative path parts preserved."""

    matches: list[tuple[int, str]] = []
    for match in OBSIDIAN_EMBED_RE.finditer(markdown_text):
        target = normalize_bundle_target(match.group(1))
        if target and not is_external_or_absolute(target):
            matches.append((match.start(), target))
    for match in MARKDOWN_IMAGE_RE.finditer(markdown_text):
        raw_target = match.group(2).strip().strip("<>")
        target = normalize_bundle_target(raw_target)
        if target and not is_external_or_absolute(target):
            matches.append((match.start(), target))

    seen: set[str] = set()
    for _position, target in sorted(matches, key=lambda item: item[0]):
        key = target.casefold()
        if key in seen:
            continue
        seen.add(key)
        yield target


def normalize_bundle_target(target: str) -> str:
    """Normalize target text while keeping useful relative path components."""

    target = unquote(target.strip().strip("<>"))
    target = target.split("#", 1)[0].strip()
    return target.replace("\\", "/")


def resolve_media_target(target: str, *, note_path: Path, vault_root: Path | None = None) -> Path | None:
    """Resolve a target from note-relative, vault-relative, or basename lookup."""

    target_path = PurePosixPath(target)
    candidates: list[Path] = []
    if not target_path.is_absolute():
        candidates.append((note_path.parent / Path(*target_path.parts)).resolve())
        if vault_root is not None:
            candidates.append((Path(vault_root).expanduser().resolve() / Path(*target_path.parts)).resolve())

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    names = {target_path.name.casefold(), target_path.stem.casefold()}
    search_roots = [note_path.parent]
    if vault_root is not None:
        search_roots.append(Path(vault_root).expanduser().resolve())
    for root in search_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and (path.name.casefold() in names or path.stem.casefold() in names):
                return path.resolve()
    return None


def unique_filename(filename: str, used_names: set[str]) -> str:
    """Return a collision-free filename preserving the extension."""

    path = Path(filename)
    candidate = path.name
    counter = 2
    while candidate.casefold() in used_names:
        candidate = f"{path.stem}-{counter}{path.suffix}"
        counter += 1
    used_names.add(candidate.casefold())
    return candidate


def upsert_frontmatter_fields(markdown_text: str, *, title: str | None, description: str | None) -> str:
    """Add or replace simple frontmatter ``title``/``description`` fields."""

    metadata, body = split_frontmatter(markdown_text)
    if title is not None:
        metadata["title"] = title
    if description is not None:
        metadata["description"] = description
    lines = ["---"]
    for key, value in metadata.items():
        if "\n" in value:
            lines.append(f"{key}: |")
            lines.extend(f"  {line}" for line in value.splitlines())
        else:
            escaped = value.replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip()
