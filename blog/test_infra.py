"""Tests for observability and infrastructure: health endpoint, backup command."""

import io
import json

import pytest
from django.core.management import call_command
from django.test import Client

from blog.models import Post


@pytest.mark.django_db
def test_readiness_endpoints_return_sanitized_success():
    client = Client()
    for path in ("/api/v1/health/", "/api/v1/health/ready/"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_liveness_is_public_and_does_not_query_database(django_assert_num_queries):
    client = Client()
    with django_assert_num_queries(0):
        response = client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_health_probes_are_get_only():
    client = Client()
    for path in ("/api/v1/health/", "/api/v1/health/live/", "/api/v1/health/ready/"):
        assert client.post(path).status_code == 405


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