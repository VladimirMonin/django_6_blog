"""Focused contract tests for authenticated multipart post publication."""

import hashlib
import io
import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from api.models import ApiKey, PublishPackage
from blog.models import AuditLog, Post, PostMedia
from publisher.client import publish_package as client_publish_package
from publisher.package import build_publish_package
from publisher.parser import parse_markdown_file


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def package_manifest(post, assets):
    manifest = {"protocol_version": 1, "post": post, "assets": assets}
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    manifest["package_sha256"] = hashlib.sha256(encoded).hexdigest()
    return manifest


def asset_spec(data, *, asset_id="a001", filename="cover.png", roles=None, refs=None, mime="image/png"):
    return {
        "id": asset_id,
        "part": f"asset_{asset_id}",
        "original_filename": filename,
        "source_refs": refs or [filename],
        "roles": roles or ["body"],
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content_type": mime,
        "media_kind": mime.split("/", 1)[0],
    }


def post_package(client, key, manifest, files, idempotency_key="package-key-0001"):
    data = {"manifest": json.dumps(manifest, ensure_ascii=False), **files}
    return client.post(
        "/api/v1/posts/publish-package/",
        data=data,
        HTTP_AUTHORIZATION=f"Bearer {key.token}",
        HTTP_IDEMPOTENCY_KEY=idempotency_key,
    )


@pytest.mark.django_db
def test_publish_package_attaches_cover_body_image_and_is_idempotent(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(name="Asset Agent")
    client = Client()
    image = png_bytes()
    spec = asset_spec(image, roles=["body", "cover"])
    post = {
        "title": "Package Article",
        "description": "Published with an image",
        "content": "Body\n\n![[cover.png]]",
        "content_type": "article",
        "status": "published",
    }
    manifest = package_manifest(post, [spec])

    first = post_package(
        client,
        key,
        manifest,
        {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")},
    )
    assert first.status_code == 201, first.content
    created = Post.objects.get(slug=first.json()["slug"])
    assert created.status == Post.Status.PUBLISHED
    assert created.media_files.count() == 1
    assert created.cover_media.original_filename == "cover.png"
    assert "/media/" in created.content_html
    assert AuditLog.objects.filter(post=created, api_key=key).exists()

    replay = post_package(
        client,
        key,
        manifest,
        {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")},
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert Post.objects.filter(slug=created.slug).count() == 1
    assert PublishPackage.objects.get(api_key=key).state == PublishPackage.State.DONE


@pytest.mark.django_db
def test_publish_package_local_video_is_single_primary_and_embed_is_stripped(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(name="Video Agent")
    video = b"\x00\x00\x00\x18ftypisom" + b"0" * 64
    spec = asset_spec(
        video,
        filename="clip.mp4",
        roles=["body", "primary"],
        refs=["clip.mp4"],
        mime="video/mp4",
    )
    manifest = package_manifest(
        {
            "title": "Local Video",
            "description": "Local primary",
            "content": "Before\n\n![[clip.mp4]]\n\nAfter",
            "content_type": "video",
            "status": "published",
        },
        [spec],
    )
    response = post_package(
        Client(),
        key,
        manifest,
        {"asset_a001": SimpleUploadedFile("clip.mp4", video, content_type="video/mp4")},
        "package-video-0001",
    )
    assert response.status_code == 201, response.content
    post = Post.objects.get(slug=response.json()["slug"])
    assert post.primary_media.media_type == PostMedia.MediaType.VIDEO
    assert "clip.mp4" not in post.content
    detail = Client().get(f"/post/{post.slug}/")
    assert detail.status_code == 200
    assert detail.content.count(b"<video") == 1


@pytest.mark.django_db
def test_publish_package_rejects_conflict_traversal_mime_and_undeclared_parts(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(name="Validation Agent")
    client = Client()
    image = png_bytes()
    base_post = {"title": "Negative", "description": "Checks", "content": "Body", "content_type": "article"}
    valid = asset_spec(image)
    manifest = package_manifest(base_post, [valid])
    ok = post_package(client, key, manifest, {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")}, "negative-key-0001")
    assert ok.status_code == 201

    changed = package_manifest({**base_post, "description": "Different"}, [valid])
    conflict = post_package(client, key, changed, {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")}, "negative-key-0001")
    assert conflict.status_code == 409

    traversal_spec = asset_spec(image, refs=["../secret.png"])
    traversal = post_package(client, key, package_manifest({**base_post, "title": "Traversal"}, [traversal_spec]), {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")}, "negative-key-0002")
    assert traversal.status_code == 400
    assert "relative logical path" in traversal.json()["error"]

    wrong_mime = asset_spec(image, mime="image/jpeg")
    mime = post_package(client, key, package_manifest({**base_post, "title": "Mime"}, [wrong_mime]), {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")}, "negative-key-0003")
    assert mime.status_code == 400

    extra = post_package(
        client,
        key,
        package_manifest({**base_post, "title": "Extra"}, [valid]),
        {
            "asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png"),
            "asset_extra": SimpleUploadedFile("extra.png", image, content_type="image/png"),
        },
        "negative-key-0004",
    )
    assert extra.status_code == 400


@pytest.mark.django_db
def test_publish_package_storage_is_cleaned_when_db_finalize_fails(tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(name="Cleanup Agent")
    image = png_bytes()
    spec = asset_spec(image)
    manifest = package_manifest(
        {"title": "Cleanup", "description": "Failure", "content": "![[cover.png]]", "content_type": "article"},
        [spec],
    )
    original_save = Post.save

    def fail_new_post(self, *args, **kwargs):
        if self._state.adding:
            raise RuntimeError("forced DB failure")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(Post, "save", fail_new_post)
    response = post_package(
        Client(),
        key,
        manifest,
        {"asset_a001": SimpleUploadedFile("cover.png", image, content_type="image/png")},
        "cleanup-key-0001",
    )
    assert response.status_code == 500
    package = PublishPackage.objects.get(api_key=key)
    assert package.state == PublishPackage.State.FAILED
    assert package.storage_names == []
    assert not any(path.is_file() for path in Path(settings.MEDIA_ROOT).rglob("*"))


@pytest.mark.django_db
def test_thumbnail_generation_does_not_call_storage_path(tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    post = Post.objects.create(title="Image", description="d", content="body", slug="image-pathless")
    image = png_bytes()
    media = PostMedia.objects.create(
        post=post,
        file=SimpleUploadedFile("image.png", image, content_type="image/png"),
        original_filename="image.png",
    )

    def path_is_forbidden(*args, **kwargs):
        raise NotImplementedError("path() is unavailable")

    monkeypatch.setattr(media.file.storage, "path", path_is_forbidden)
    thumbnail = media._generate_thumbnail((40, 30))
    assert thumbnail.size > 0


@pytest.mark.django_db
def test_stdlib_publisher_streams_local_image_package(tmp_path, settings, live_server):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(name="Publisher Package Agent")
    note = tmp_path / "note.md"
    (tmp_path / "picture.png").write_bytes(png_bytes())
    note.write_text(
        "---\ntitle: CLI Package\ndescription: image package\ncover: picture.png\n---\nBody\n\n![[picture.png]]\n",
        encoding="utf-8",
    )
    payload = parse_markdown_file(note)
    manifest, files, default_key = build_publish_package(note, payload)
    assert files
    assert all(not str(path).startswith(str(tmp_path)) for asset in manifest["assets"] for path in asset["source_refs"])
    result = client_publish_package(
        url=live_server.url,
        api_key=key.token,
        manifest=manifest,
        files=files,
        idempotency_key=default_key,
    )
    post = Post.objects.get(slug=result["slug"])
    assert post.status == Post.Status.PUBLISHED
    assert post.cover_media is not None
    assert Client().get(f"/post/{post.slug}/").status_code == 200


@pytest.mark.django_db(transaction=True)
def test_replace_stays_committed_when_old_storage_cleanup_fails(tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(name="Replacement cleanup agent")
    client = Client()
    old_image = png_bytes()
    old_spec = asset_spec(old_image, filename="old.png", roles=["body", "cover"])
    old_manifest = package_manifest(
        {
            "title": "Replacement cleanup",
            "description": "old",
            "content": "![[old.png]]",
            "content_type": "article",
            "slug": "replacement-cleanup",
        },
        [old_spec],
    )
    first = post_package(
        client,
        key,
        old_manifest,
        {"asset_a001": SimpleUploadedFile("old.png", old_image, content_type="image/png")},
        "replace-cleanup-old",
    )
    assert first.status_code == 201
    post = Post.objects.get(slug="replacement-cleanup")
    old_media = post.media_files.get()
    old_names = {
        name
        for name in (old_media.file.name, old_media.thumbnail_og.name, old_media.thumbnail_card.name)
        if name
    }
    storage = old_media.file.storage
    original_delete = storage.delete

    def fail_old_delete(name):
        if name in old_names:
            raise OSError("object storage cleanup unavailable")
        return original_delete(name)

    monkeypatch.setattr(storage, "delete", fail_old_delete)
    new_image = png_bytes()
    new_spec = asset_spec(new_image, filename="new.png", roles=["body", "cover"])
    new_manifest = package_manifest(
        {
            "title": "Replacement cleanup",
            "description": "new",
            "content": "![[new.png]]",
            "content_type": "article",
            "slug": "replacement-cleanup",
            "replace": True,
        },
        [new_spec],
    )

    replaced = post_package(
        client,
        key,
        new_manifest,
        {"asset_a001": SimpleUploadedFile("new.png", new_image, content_type="image/png")},
        "replace-cleanup-new",
    )

    assert replaced.status_code == 201, replaced.content
    post.refresh_from_db()
    assert post.description == "new"
    assert post.media_files.get().original_filename == "new.png"
    assert PublishPackage.objects.get(
        idempotency_key="replace-cleanup-new"
    ).state == PublishPackage.State.DONE
