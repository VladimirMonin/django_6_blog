"""Validated, idempotent multipart publication of posts with local assets."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from blog.content_import.obsidian import is_standalone_player_media_embed
from blog.content_import.timecodes import time_to_seconds
from blog.models import AuditLog, Category, Post, PostMedia, Series, Tag
from blog.slug_utils import build_slug

from .models import PublishPackage
from .serializers import serialize_post

logger = logging.getLogger("api.package_publish")

MANIFEST_MAX = 256 * 1024
CONTENT_MAX = 2 * 1024 * 1024
ASSET_MAX_COUNT = 32
PACKAGE_MAX = 512 * 1024 * 1024
IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9._-]{8,128}$")
ASSET_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ALLOWED_ROLES = {"body", "cover", "primary"}

TYPE_RULES = {
    ".jpg": ("image/jpeg", "image", 20 * 1024 * 1024),
    ".jpeg": ("image/jpeg", "image", 20 * 1024 * 1024),
    ".png": ("image/png", "image", 20 * 1024 * 1024),
    ".webp": ("image/webp", "image", 20 * 1024 * 1024),
    ".gif": ("image/gif", "image", 20 * 1024 * 1024),
    ".mp4": ("video/mp4", "video", 500 * 1024 * 1024),
    ".webm": ("video/webm", "video", 500 * 1024 * 1024),
    ".mp3": ("audio/mpeg", "audio", 200 * 1024 * 1024),
    ".ogg": ("audio/ogg", "audio", 200 * 1024 * 1024),
    ".opus": ("audio/ogg", "audio", 200 * 1024 * 1024),
    ".wav": ("audio/wav", "audio", 200 * 1024 * 1024),
    ".flac": ("audio/flac", "audio", 200 * 1024 * 1024),
    ".m4a": ("audio/mp4", "audio", 200 * 1024 * 1024),
}


class PackageError(ValueError):
    """Safe client-facing package validation error."""


class PackageConflict(PackageError):
    """Safe conflict raised for reused keys or existing posts."""


@dataclass
class ValidatedAsset:
    spec: dict
    upload: object
    extension: str
    media_kind: str


def _limit(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def canonical_package_hash(manifest: dict) -> str:
    payload = {key: value for key, value in manifest.items() if key != "package_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe_source_ref(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise PackageError("asset source_refs must contain non-empty strings")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or normalized.startswith(("/", "~")):
        raise PackageError("asset source_ref must be a relative logical path")
    return normalized


def _matches_magic(extension: str, head: bytes) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return head.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    if extension == ".gif":
        return head.startswith((b"GIF87a", b"GIF89a"))
    if extension in {".mp4", ".m4a"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if extension == ".webm":
        return head.startswith(b"\x1aE\xdf\xa3")
    if extension == ".mp3":
        return head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    if extension in {".ogg", ".opus"}:
        return head.startswith(b"OggS")
    if extension == ".wav":
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if extension == ".flac":
        return head.startswith(b"fLaC")
    return False


def parse_manifest(request) -> dict:
    raw = request.POST.get("manifest")
    if raw is None:
        raise PackageError("manifest part is required")
    raw_bytes = raw.encode("utf-8")
    if len(raw_bytes) > _limit("PUBLISH_PACKAGE_MANIFEST_MAX", MANIFEST_MAX):
        raise PackageError("manifest exceeds size limit")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PackageError("manifest is not valid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("protocol_version") != 1:
        raise PackageError("unsupported manifest protocol_version")
    return manifest


def validate_request(request, manifest: dict) -> tuple[dict, list[ValidatedAsset], str]:
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not IDEMPOTENCY_RE.fullmatch(idempotency_key):
        raise PackageError("valid Idempotency-Key header is required")
    post_data = manifest.get("post")
    specs = manifest.get("assets")
    claimed_hash = manifest.get("package_sha256")
    calculated_hash = canonical_package_hash(manifest)
    if not isinstance(claimed_hash, str) or claimed_hash != calculated_hash:
        raise PackageError("package_sha256 mismatch")
    if not isinstance(post_data, dict) or not isinstance(specs, list):
        raise PackageError("manifest post and assets are required")
    content = post_data.get("content")
    if not isinstance(content, str) or not content:
        raise PackageError("post content is required")
    if len(content.encode("utf-8")) > _limit("PUBLISH_PACKAGE_CONTENT_MAX", CONTENT_MAX):
        raise PackageError("post content exceeds size limit")
    for field in ("title", "description"):
        if not isinstance(post_data.get(field), str) or not post_data[field].strip():
            raise PackageError(f"post {field} is required")
    if len(post_data["title"].strip()) > 200:
        raise PackageError("post title exceeds size limit")
    content_type = str(post_data.get("content_type") or "article").casefold()
    if content_type not in {"article", "video", "audio", "podcast"}:
        raise PackageError("post content_type is invalid")
    if post_data.get("status", "published") not in {"published", "draft"}:
        raise PackageError("post status is invalid")
    source_id = post_data.get("source_id")
    if source_id is not None and (not isinstance(source_id, str) or len(source_id.strip()) > 200):
        raise PackageError("post source_id is invalid")
    if len(specs) > _limit("PUBLISH_PACKAGE_ASSET_MAX_COUNT", ASSET_MAX_COUNT):
        raise PackageError("asset count exceeds limit")

    ids: set[str] = set()
    parts: set[str] = set()
    names: set[str] = set()
    assets: list[ValidatedAsset] = []
    role_counts = {"cover": 0, "primary": 0}
    total_size = 0
    expected_parts: set[str] = set()

    for spec in specs:
        if not isinstance(spec, dict):
            raise PackageError("each asset must be an object")
        asset_id = spec.get("id")
        part = spec.get("part")
        filename = spec.get("original_filename")
        roles = spec.get("roles", [])
        refs = spec.get("source_refs", [])
        if not isinstance(asset_id, str) or not ASSET_ID_RE.fullmatch(asset_id):
            raise PackageError("invalid asset id")
        if part != f"asset_{asset_id}" or part in parts or asset_id in ids:
            raise PackageError(f"asset {asset_id}: invalid or duplicate part")
        if not isinstance(filename, str) or PurePosixPath(filename).name != filename or "\\" in filename:
            raise PackageError(f"asset {asset_id}: original_filename must be a basename")
        name_key = filename.casefold()
        if name_key in names:
            raise PackageError(f"asset {asset_id}: duplicate original_filename")
        extension = PurePosixPath(filename).suffix.casefold()
        if extension not in TYPE_RULES:
            raise PackageError(f"asset {asset_id}: unsupported file type")
        expected_mime, media_kind, default_max = TYPE_RULES[extension]
        if not isinstance(roles, list) or not roles or set(roles) - ALLOWED_ROLES:
            raise PackageError(f"asset {asset_id}: invalid roles")
        if not isinstance(refs, list):
            raise PackageError(f"asset {asset_id}: source_refs must be a list")
        spec["source_refs"] = [_safe_source_ref(ref) for ref in refs]
        for role in ("cover", "primary"):
            if role in roles:
                role_counts[role] += 1
        if "cover" in roles and media_kind != "image":
            raise PackageError(f"asset {asset_id}: cover must be an image")
        upload = request.FILES.get(part)
        if upload is None:
            raise PackageError(f"asset {asset_id}: upload part is missing")
        declared_size = spec.get("size")
        if not isinstance(declared_size, int) or declared_size <= 0 or declared_size != upload.size:
            raise PackageError(f"asset {asset_id}: size mismatch")
        max_size = _limit(f"PUBLISH_PACKAGE_{media_kind.upper()}_MAX", default_max)
        if upload.size > max_size:
            raise PackageError(f"asset {asset_id}: file exceeds size limit")
        digest = hashlib.sha256()
        head = b""
        for chunk in upload.chunks():
            if len(head) < 16:
                head += chunk[: 16 - len(head)]
            digest.update(chunk)
        upload.seek(0)
        if digest.hexdigest() != spec.get("sha256"):
            raise PackageError(f"asset {asset_id}: sha256 mismatch")
        if not _matches_magic(extension, head):
            raise PackageError(f"asset {asset_id}: file signature mismatch")
        declared_mime = spec.get("content_type") or getattr(upload, "content_type", "")
        if declared_mime and declared_mime != expected_mime:
            raise PackageError(f"asset {asset_id}: MIME type mismatch")
        spec["media_kind"] = media_kind
        ids.add(asset_id)
        parts.add(part)
        names.add(name_key)
        expected_parts.add(part)
        total_size += upload.size
        assets.append(ValidatedAsset(spec, upload, extension, media_kind))

    if set(request.FILES) != expected_parts:
        raise PackageError("multipart request contains undeclared file parts")
    if total_size > _limit("PUBLISH_PACKAGE_TOTAL_MAX", PACKAGE_MAX):
        raise PackageError("package exceeds total size limit")
    if role_counts["cover"] > 1 or role_counts["primary"] > 1:
        raise PackageError("package allows at most one cover and one primary asset")

    primary = next((asset for asset in assets if "primary" in asset.spec["roles"]), None)
    media_url = str(post_data.get("media_url") or "").strip()
    if content_type == "article" and primary:
        raise PackageError("article cannot have a primary asset")
    if content_type in {"video", "audio", "podcast"}:
        if bool(primary) == bool(media_url):
            raise PackageError("media post requires exactly one external media_url or local primary")
        expected_kind = "video" if content_type == "video" else "audio"
        if primary and primary.media_kind != expected_kind:
            raise PackageError("primary asset kind does not match content_type")
    return post_data, assets, calculated_hash


def _normalize_timecodes(raw: object) -> list[dict]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise PackageError("post timecodes must be a list")
    normalized = []
    for index, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict) or not str(entry.get("label") or "").strip():
            raise PackageError(f"timecode #{index} is invalid")
        try:
            seconds = time_to_seconds(entry.get("time"))
        except (TypeError, ValueError) as exc:
            raise PackageError(f"timecode #{index} is invalid") from exc
        normalized.append({"time": entry["time"], "seconds": seconds, "label": entry["label"]})
    return normalized


def _delete_replaced_storage_names(storage, names: tuple[str, ...]) -> None:
    """Best-effort cleanup after the replacement transaction committed."""
    for name in names:
        try:
            storage.delete(name)
        except Exception:
            logger.warning(
                "api.publish_package.old_asset_cleanup_failed",
                extra={"storage_name": name},
            )


def _cleanup_new_storage_names(storage, names: list[str]) -> list[str]:
    """Delete newly owned objects and return names that still need recovery."""
    remaining = []
    for name in reversed(names):
        try:
            storage.delete(name)
        except Exception:
            remaining.append(name)
            logger.warning(
                "api.publish_package.new_asset_cleanup_failed",
                extra={"storage_name": name},
            )
    remaining.reverse()
    return remaining


def _strip_primary_embed(content: str, primary: ValidatedAsset | None) -> str:
    if not primary:
        return content
    targets = {PurePosixPath(ref).name.casefold() for ref in primary.spec["source_refs"]}
    targets.add(primary.spec["original_filename"].casefold())
    lines = [line for line in content.splitlines() if not is_standalone_player_media_embed(line, targets)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def publish_validated_package(*, request, manifest: dict, post_data: dict, assets: list[ValidatedAsset], payload_hash: str):
    api_key = request.api_key
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not IDEMPOTENCY_RE.fullmatch(idempotency_key):
        raise PackageError("valid Idempotency-Key header is required")

    try:
        with transaction.atomic():
            package, created = PublishPackage.objects.select_for_update().get_or_create(
                api_key=api_key,
                idempotency_key=idempotency_key,
                defaults={"payload_sha256": payload_hash},
            )
    except IntegrityError:
        package = PublishPackage.objects.get(api_key=api_key, idempotency_key=idempotency_key)
        created = False
    if not created:
        if package.payload_sha256 != payload_hash:
            raise PackageConflict("idempotency key was already used for a different package")
        if package.state == PublishPackage.State.DONE:
            return package.response, 200
        raise PackageConflict("package with this idempotency key is already pending or failed")

    slug = str(post_data.get("slug") or "").strip() or build_slug(post_data["title"], fallback="post")
    storage = PostMedia._meta.get_field("file").storage
    stored_names: list[str] = []
    old_names: list[str] = []
    try:
        for asset in assets:
            desired = f"posts/{slug}/packages/{idempotency_key}/{asset.spec['id']}{asset.extension}"
            actual = storage.save(desired, asset.upload)
            if actual != desired:
                raise PackageError(f"asset {asset.spec['id']}: deterministic storage name is unavailable")
            stored_names.append(actual)
        package.storage_names = stored_names
        package.save(update_fields=["storage_names", "updated_at"])

        with transaction.atomic():
            source_id = str(post_data.get("source_id") or "").strip() or None
            existing = None
            if source_id:
                existing = Post.objects.select_for_update().filter(source_id=source_id, deleted_at__isnull=True).first()
            if existing is None:
                existing = Post.objects.select_for_update().filter(slug=slug, deleted_at__isnull=True).first()
            replace = bool(post_data.get("replace")) or bool(source_id and existing)
            if existing and not replace:
                raise PackageConflict(f"post with slug '{slug}' already exists; use replace=true")

            category_name = str(post_data.get("category") or "").strip()
            series_name = str(post_data.get("series") or "").strip()
            category = Category.objects.get_or_create(name=category_name)[0] if category_name else None
            series = Series.objects.get_or_create(name=series_name)[0] if series_name else None
            primary = next((asset for asset in assets if "primary" in asset.spec["roles"]), None)
            content = _strip_primary_embed(post_data["content"], primary)
            fields = {
                "title": post_data["title"].strip(),
                "description": post_data["description"].strip(),
                "slug": existing.slug if existing and source_id else slug,
                "content": content,
                "content_type": str(post_data.get("content_type") or "article").casefold(),
                "media_url": str(post_data.get("media_url") or "").strip(),
                "timecodes": _normalize_timecodes(post_data.get("timecodes")),
                "status": Post.Status.DRAFT,
                "category": category,
                "series": series,
                "series_order": int(post_data.get("series_order", 0) or 0),
                "source_id": source_id,
                "deleted_at": None,
            }
            if existing:
                post = existing
                for name, value in fields.items():
                    setattr(post, name, value)
                for media in post.media_files.all():
                    old_names.extend(name for name in (media.file.name, media.thumbnail_og.name, media.thumbnail_card.name) if name)
                post.media_files.all().delete()
                post.save()
                action = AuditLog.Action.UPDATED
            else:
                post = Post.objects.create(**fields)
                action = AuditLog.Action.PUBLISHED

            asset_storage_names = list(stored_names)
            storage_by_id = {
                asset.spec["id"]: storage_name
                for asset, storage_name in zip(assets, asset_storage_names, strict=True)
            }
            ordered_assets = sorted(
                assets,
                key=lambda asset: (
                    0 if "cover" in asset.spec["roles"] else 1 if "primary" in asset.spec["roles"] else 2,
                    asset.spec["id"],
                ),
            )
            for asset in ordered_assets:
                storage_name = storage_by_id[asset.spec["id"]]
                media = PostMedia.objects.create(
                    post=post,
                    file=storage_name,
                    original_filename=asset.spec["original_filename"],
                )
                stored_names.extend(name for name in (media.thumbnail_og.name, media.thumbnail_card.name) if name)
            post.content = content
            post.status = Post.Status.DRAFT if post_data.get("status") == "draft" else Post.Status.PUBLISHED
            post.save()
            tag_names = post_data.get("tags") or []
            if not isinstance(tag_names, list):
                raise PackageError("post tags must be a list")
            post.tags.set(Tag.objects.get_or_create(name=str(name).strip())[0] for name in tag_names if str(name).strip())
            AuditLog.log(
                action=action,
                post=post,
                api_key=api_key,
                detail={"source_id": source_id, "content_type": post.content_type, "package_id": package.pk, "asset_count": len(assets)},
            )
            response = serialize_post(post)
            package.post = post
            package.state = PublishPackage.State.DONE
            package.storage_names = stored_names
            package.response = response
            package.save(update_fields=["post", "state", "storage_names", "response", "updated_at"])
            if old_names:
                transaction.on_commit(
                    lambda names=tuple(old_names): _delete_replaced_storage_names(storage, names)
                )
        return response, 201
    except Exception:
        for name in reversed(stored_names):
            try:
                storage.delete(name)
            except Exception:
                pass
        PublishPackage.objects.filter(pk=package.pk).update(
            state=PublishPackage.State.FAILED,
            storage_names=[],
            updated_at=timezone.now(),
        )
        raise
