"""Offline storage compatibility and compensating-cleanup tests."""

from io import BytesIO

import pytest
from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage
from django.db import models
from PIL import Image

from blog.models import Post, PostMedia


@pytest.fixture(autouse=True)
def restore_post_media_storages():
    fields = [
        PostMedia._meta.get_field("file"),
        PostMedia._meta.get_field("thumbnail_og"),
        PostMedia._meta.get_field("thumbnail_card"),
    ]
    original = [field.storage for field in fields]
    yield
    for field, storage in zip(fields, original, strict=True):
        field.storage = storage


class PathlessStorage(Storage):
    """In-memory backend that records access and has no filesystem path API."""

    def __init__(self):
        self.files = {}
        self.open_count = 0
        self.deleted_names = []
        self.fail_on_save_number = None
        self.save_count = 0

    def path(self, name):
        raise NotImplementedError("path() is unavailable")

    def _open(self, name, mode="rb"):
        self.open_count += 1
        return File(BytesIO(self.files[name]), name=name)

    def _save(self, name, content):
        self.save_count += 1
        if self.save_count == self.fail_on_save_number:
            raise OSError("injected storage write failure")
        self.files[name] = content.read()
        return name

    def delete(self, name):
        self.deleted_names.append(name)
        self.files.pop(name, None)

    def exists(self, name):
        return name in self.files

    def url(self, name):
        return f"/test-media/{name}"


def image_bytes(color="red"):
    buffer = BytesIO()
    Image.new("RGB", (32, 24), color).save(buffer, format="PNG")
    return buffer.getvalue()


def create_image_media(storage, *, post_slug="storage-post", filename="cover.png"):
    post = Post.objects.create(
        title=post_slug,
        description="storage compatibility",
        content="body",
        slug=post_slug,
    )
    source_name = storage.save(
        f"posts/{post_slug}/{filename}", ContentFile(image_bytes())
    )
    field = PostMedia._meta.get_field("file")
    field.storage = storage
    PostMedia._meta.get_field("thumbnail_og").storage = storage
    PostMedia._meta.get_field("thumbnail_card").storage = storage
    media = PostMedia.objects.create(
        post=post,
        file=source_name,
        original_filename=filename,
    )
    return media, source_name


@pytest.mark.django_db
def test_pathless_storage_reads_source_once_and_creates_expected_derivatives():
    storage = PathlessStorage()

    media, source_name = create_image_media(storage)

    assert storage.open_count == 1
    assert media.thumbnail_og.name == "posts/storage-post/thumbnails/cover.png_og.jpg"
    assert media.thumbnail_card.name == "posts/storage-post/thumbnails/cover.png_card.jpg"
    assert storage.exists(source_name)
    with Image.open(storage.open(media.thumbnail_og.name)) as thumbnail:
        assert thumbnail.size == (1200, 630)
    with Image.open(storage.open(media.thumbnail_card.name)) as thumbnail:
        assert thumbnail.size == (400, 300)


@pytest.mark.django_db
def test_second_thumbnail_write_failure_removes_first_derivative_and_allows_retry():
    storage = PathlessStorage()
    storage.fail_on_save_number = 3  # source, OG, then injected card failure

    media, source_name = create_image_media(storage, post_slug="write-failure")

    media.refresh_from_db()
    assert storage.exists(source_name)
    assert not media.thumbnail_og
    assert not media.thumbnail_card
    assert "posts/write-failure/thumbnails/cover.png_og.jpg" in storage.deleted_names
    assert not storage.exists("posts/write-failure/thumbnails/cover.png_og.jpg")

    storage.fail_on_save_number = None
    media.save()
    media.refresh_from_db()
    assert storage.exists(media.thumbnail_og.name)
    assert storage.exists(media.thumbnail_card.name)


@pytest.mark.django_db
def test_thumbnail_db_update_failure_compensates_both_new_objects(monkeypatch):
    storage = PathlessStorage()
    original_save = models.Model.save
    media_save_calls = 0

    def fail_thumbnail_update(instance, *args, **kwargs):
        nonlocal media_save_calls
        if isinstance(instance, PostMedia):
            media_save_calls += 1
            if media_save_calls == 2:
                raise RuntimeError("injected DB update failure")
        return original_save(instance, *args, **kwargs)

    monkeypatch.setattr(models.Model, "save", fail_thumbnail_update)
    media, source_name = create_image_media(storage, post_slug="db-failure")

    media.refresh_from_db()
    assert storage.exists(source_name)
    assert not media.thumbnail_og
    assert not media.thumbnail_card
    assert not storage.exists("posts/db-failure/thumbnails/cover.png_og.jpg")
    assert not storage.exists("posts/db-failure/thumbnails/cover.png_card.jpg")

    media.save()
    media.refresh_from_db()
    assert storage.exists(media.thumbnail_og.name)
    assert storage.exists(media.thumbnail_card.name)


@pytest.mark.django_db
def test_post_scoped_thumbnail_names_isolate_duplicate_filenames():
    storage = PathlessStorage()

    first, _ = create_image_media(storage, post_slug="first-post")
    second, _ = create_image_media(storage, post_slug="second-post")

    assert first.thumbnail_og.name != second.thumbnail_og.name
    assert first.thumbnail_card.name != second.thumbnail_card.name
    assert storage.exists(first.thumbnail_og.name)
    assert storage.exists(second.thumbnail_og.name)
