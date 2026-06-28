"""Tests for observability and infrastructure: health endpoint, backup command."""

import io
import json

import pytest
from django.core.management import call_command
from django.test import Client

from blog.models import Post


@pytest.mark.django_db
def test_health_endpoint_returns_200_and_correct_shape():
    """Health endpoint returns 200 with status, db, post_count, version keys."""
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert "post_count" in data
    assert isinstance(data["post_count"], int)
    assert data["version"] == "1.0"


@pytest.mark.django_db
def test_health_endpoint_works_without_api_key():
    """Health endpoint is public — no Authorization header required."""
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    # Must not return 401 or 403
    assert response.status_code not in (401, 403)


@pytest.mark.django_db
def test_health_endpoint_shows_correct_post_count():
    """Health endpoint post_count matches the number of non-deleted posts."""
    # Clean slate — delete all posts
    for post in Post.objects.all():
        post.hard_delete()

    Post.objects.create(
        title="Test Post 1",
        slug="test-post-1",
        content="Content 1",
        status=Post.Status.PUBLISHED,
    )
    Post.objects.create(
        title="Test Post 2",
        slug="test-post-2",
        content="Content 2",
        status=Post.Status.DRAFT,
    )

    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["post_count"] == 2


@pytest.mark.django_db
def test_backup_command_outputs_valid_json_with_posts():
    """backup command outputs valid JSON containing posts array."""
    Post.objects.create(
        title="Backup Test",
        slug="backup-test",
        content="Backup content",
        status=Post.Status.PUBLISHED,
    )

    out = io.StringIO()
    call_command("backup", stdout=out)
    output = out.getvalue()

    data = json.loads(output)
    assert "posts" in data
    assert isinstance(data["posts"], list)
    assert len(data["posts"]) >= 1
    # Each serialized post should have model and fields
    assert data["posts"][0]["model"] == "blog.post"
    assert "fields" in data["posts"][0]


@pytest.mark.django_db
def test_backup_command_writes_to_file():
    """backup --output writes JSON to the specified file."""
    import tempfile
    from pathlib import Path

    Post.objects.create(
        title="File Backup Test",
        slug="file-backup-test",
        content="File backup content",
        status=Post.Status.PUBLISHED,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        outfile = Path(tmpdir) / "backup.json"
        call_command("backup", "--output", str(outfile))

        assert outfile.exists()
        data = json.loads(outfile.read_text(encoding="utf-8"))
        assert "posts" in data
        assert any(
            p["fields"]["slug"] == "file-backup-test" for p in data["posts"]
        )