"""Build safe multipart publication packages without Django dependencies."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .parser import split_frontmatter

OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
MARKDOWN_EMBED_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_RE = re.compile(r"^https?://", re.I)
ALLOWED_EXTENSIONS = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".mp4": "video/mp4",
    ".webm": "video/webm", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
    ".opus": "audio/ogg", ".wav": "audio/wav", ".flac": "audio/flac",
    ".m4a": "audio/mp4",
}


def _canonical_hash(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "package_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _logical_target(raw: str) -> str:
    target = raw.strip().strip("<>").replace("\\", "/")
    path = PurePosixPath(target)
    if (
        not target
        or any(ord(character) < 32 for character in target)
        or path.is_absolute()
        or ".." in path.parts
        or target.startswith("~")
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target)
    ):
        raise ValueError("Local asset reference must stay inside --assets-dir")
    return target


def _is_external(target: str) -> bool:
    return bool(EXTERNAL_RE.match(target.strip()))


def _resolve_asset(root: Path, logical: str) -> Path:
    root = root.resolve()
    candidate = (root / logical).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Local asset reference escapes --assets-dir") from exc
    if not candidate.is_file():
        raise ValueError(f"Local asset is missing: {PurePosixPath(logical).name}")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_publish_package(
    note_path: Path,
    payload: dict[str, Any],
    *,
    assets_dir: Path | None = None,
    replace: bool = False,
) -> tuple[dict[str, Any], dict[str, Path], str]:
    """Return manifest, upload part paths, and deterministic idempotency key."""
    note_path = Path(note_path)
    root = Path(assets_dir) if assets_dir else note_path.parent
    raw = note_path.read_text(encoding="utf-8")
    metadata, _ = split_frontmatter(raw)
    content = payload.get("content", "")

    refs: list[str] = []
    for match in OBSIDIAN_EMBED_RE.finditer(content):
        refs.append(_logical_target(match.group(1)))
    for match in MARKDOWN_EMBED_RE.finditer(content):
        raw_target = match.group(1).strip()
        if _is_external(raw_target):
            continue
        refs.append(_logical_target(raw_target))

    body_refs = set(refs)
    cover = str(metadata.get("cover") or "").strip().strip("\"'")
    cover_match = re.fullmatch(r"!?\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", cover)
    if cover_match:
        cover = cover_match.group(1)
    if cover:
        if _is_external(cover):
            raise ValueError("Cover must be a local image inside --assets-dir")
        cover = _logical_target(cover)
        refs.append(cover)

    content_type = payload.get("content_type", "article")
    media_url = str(payload.get("media_url") or "").strip()
    local_primary_ref = ""
    if content_type in {"video", "audio", "podcast"} and media_url and not _is_external(media_url):
        local_primary_ref = _logical_target(media_url)
        refs.append(local_primary_ref)

    by_path: dict[Path, dict[str, Any]] = {}
    order: list[Path] = []
    for ref in refs:
        path = _resolve_asset(root, ref)
        extension = path.suffix.casefold()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported local asset type: {path.name}")
        if path.stat().st_size <= 0:
            raise ValueError(f"Local asset is empty: {path.name}")
        if path not in by_path:
            by_path[path] = {"refs": [], "roles": []}
            order.append(path)
        if ref not in by_path[path]["refs"]:
            by_path[path]["refs"].append(ref)
        if ref in body_refs and "body" not in by_path[path]["roles"]:
            by_path[path]["roles"].append("body")
        if ref == cover and "cover" not in by_path[path]["roles"]:
            by_path[path]["roles"].append("cover")

    if cover:
        cover_path = _resolve_asset(root, cover)
        if not ALLOWED_EXTENSIONS[cover_path.suffix.casefold()].startswith("image/"):
            raise ValueError("Cover must be an image")

    if content_type in {"video", "audio", "podcast"}:
        expected = {".mp4", ".webm"} if content_type == "video" else {".mp3", ".ogg", ".opus", ".wav", ".flac", ".m4a"}
        candidates = [path for path in order if path.suffix.casefold() in expected]
        if media_url and _is_external(media_url):
            if candidates:
                raise ValueError("Media post cannot combine external media_url with local primary media")
            primary = None
        elif local_primary_ref:
            primary = _resolve_asset(root, local_primary_ref)
            if primary.suffix.casefold() not in expected:
                raise ValueError("Local primary asset kind does not match content_type")
        elif len(candidates) == 1:
            primary = candidates[0]
        elif len(candidates) > 1:
            raise ValueError("Media post has multiple local primary candidates; use media_url to select one")
        else:
            primary = None
        if primary is None and not (media_url and _is_external(media_url)):
            raise ValueError("Media post requires an external media_url or one local primary asset")
        if primary is not None and "primary" not in by_path[primary]["roles"]:
            by_path[primary]["roles"].append("primary")

    assets: list[dict[str, Any]] = []
    parts: dict[str, Path] = {}
    seen_names: set[str] = set()
    for index, path in enumerate(order, start=1):
        if path.name.casefold() in seen_names:
            raise ValueError(f"Duplicate normalized asset filename: {path.name}")
        seen_names.add(path.name.casefold())
        asset_id = f"a{index:03d}"
        part = f"asset_{asset_id}"
        mime = ALLOWED_EXTENSIONS[path.suffix.casefold()]
        assets.append({
            "id": asset_id,
            "part": part,
            "original_filename": path.name,
            "source_refs": by_path[path]["refs"],
            "roles": by_path[path]["roles"],
            "size": path.stat().st_size,
            "sha256": _sha256(path),
            "content_type": mime,
            "media_kind": mime.split("/", 1)[0],
        })
        parts[part] = path

    post = dict(payload)
    if local_primary_ref:
        post.pop("media_url", None)
    if replace:
        post["replace"] = True
    manifest: dict[str, Any] = {"protocol_version": 1, "post": post, "assets": assets}
    manifest["package_sha256"] = _canonical_hash(manifest)
    return manifest, parts, manifest["package_sha256"]
