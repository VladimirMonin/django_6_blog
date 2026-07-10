"""Independent live-HTTP review gates for multipart remote publication."""

import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.test import Client, override_settings
from PIL import Image

from api.models import ApiKey, PublishPackage
from blog.models import AuditLog, Post, PostMedia


META_RE = re.compile(r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"')
JSON_LD_RE = re.compile(
    r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def _png_bytes(color: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (12, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _run_cli(
    note: Path,
    live_server,
    token: str | None,
    *,
    env: dict[str, str] | None = None,
):
    command = [
        sys.executable,
        "-m",
        "publisher",
        "publish",
        str(note),
        "--url",
        live_server.url,
    ]
    if token is not None:
        command.extend(["--key", token])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def _publish(note: Path, live_server, token: str) -> dict:
    result = _run_cli(note, live_server, token)
    assert result.returncode == 0, result.stderr
    slug_match = re.search(r"^  Slug: (.+)$", result.stdout, re.MULTILINE)
    status_match = re.search(r"^  Status: (.+)$", result.stdout, re.MULTILINE)
    assert slug_match and status_match, result.stdout
    return {"slug": slug_match.group(1), "status": status_match.group(1)}


def _meta(document: str) -> dict[str, str]:
    return dict(META_RE.findall(document))


@pytest.mark.django_db(transaction=True)
def test_cli_live_http_article_assets_idempotency_and_secure_social_contract(
    tmp_path,
    settings,
    live_server,
):
    settings.MEDIA_ROOT = tmp_path / "media"
    key = ApiKey.objects.create(
        name="Remote article reviewer",
        token="-" + "r" * 42,
    )
    for filename, color in (
        ("cover.png", "navy"),
        ("diagram.png", "red"),
        ("second.png", "green"),
    ):
        (tmp_path / filename).write_bytes(_png_bytes(color))
    note = tmp_path / "article.md"
    note.write_text(
        "---\n"
        "title: Remote Article E2E\n"
        "description: Multipart article review\n"
        "cover: cover.png\n"
        "source_id: remote-article-e2e\n"
        "---\n"
        "Body before.\n\n![[diagram.png]]\n\n![Second](second.png)\n",
        encoding="utf-8",
    )

    unauthorized = _run_cli(note, live_server, "invalid-token")
    assert unauthorized.returncode == 1
    assert "API error (401)" in unauthorized.stderr
    assert not Post.objects.exists()
    assert not PublishPackage.objects.exists()

    first = _publish(note, live_server, key.token)
    replay = _publish(note, live_server, key.token)
    assert replay == first

    post = Post.objects.get(slug=first["slug"])
    media = list(post.media_files.all())
    assert post.status == Post.Status.PUBLISHED
    assert [item.original_filename for item in media] == [
        "cover.png",
        "diagram.png",
        "second.png",
    ]
    assert post.cover_media.original_filename == "cover.png"
    assert post.media_files.count() == 3
    assert post.content_html.count("/media/") == 2
    assert "![[diagram.png]]" not in post.content_html
    assert "(second.png)" not in post.content_html
    assert all(item.file.storage.exists(item.file.name) for item in media)
    assert post.cover_media.thumbnail_og
    assert post.cover_media.file.storage.exists(post.cover_media.thumbnail_og.name)
    assert PublishPackage.objects.get(api_key=key).state == PublishPackage.State.DONE
    assert AuditLog.objects.filter(post=post, api_key=key).count() == 1

    public = Client()
    listing = public.get("/")
    detail = public.get(post.get_absolute_url())
    assert listing.status_code == detail.status_code == 200
    assert b"Remote Article E2E" in listing.content
    assert b"Remote Article E2E" in detail.content

    with override_settings(ALLOWED_HOSTS=["blog.example"]):
        secure = Client()
        secure_detail = secure.get(
            post.get_absolute_url(),
            secure=True,
            HTTP_HOST="blog.example",
        )
        assert secure_detail.status_code == 200
        document = secure_detail.content.decode()
        meta = _meta(document)
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', document).group(1)
        structured = json.loads(JSON_LD_RE.search(document).group(1))
        assert canonical == f"https://blog.example{post.get_absolute_url()}"
        assert meta["og:url"] == canonical
        assert meta["og:image"].startswith("https://blog.example/media/")
        assert meta["twitter:image"] == meta["og:image"]
        assert structured["url"] == canonical
        assert structured["image"] == meta["og:image"]

        sitemap = secure.get("/sitemap.xml", secure=True, HTTP_HOST="blog.example")
        robots = secure.get("/robots.txt", secure=True, HTTP_HOST="blog.example")
        assert sitemap.status_code == robots.status_code == 200
        assert canonical in sitemap.content.decode()
        assert "Sitemap: https://blog.example/sitemap.xml" in robots.content.decode()


@pytest.mark.django_db(transaction=True)
def test_cli_live_http_leading_dash_key_from_environment(tmp_path, live_server):
    token = "-" + "e" * 42
    ApiKey.objects.create(name="Environment key reviewer", token=token)
    note = tmp_path / "environment-key.md"
    note.write_text(
        "---\n"
        "title: Environment Key E2E\n"
        "description: Environment key compatibility\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )
    env = {**os.environ, "BLOG_API_KEY": token}

    result = _run_cli(note, live_server, None, env=env)

    assert result.returncode == 0, result.stderr
    assert token not in result.stdout
    assert token not in result.stderr
    assert Post.objects.filter(title="Environment Key E2E").exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("content_type", "filename", "signature", "player_tag"),
    [
        ("video", "primary.mp4", b"\x00\x00\x00\x18ftypisom" + b"v" * 64, "video"),
        ("podcast", "primary.opus", b"OggS" + b"a" * 64, "audio"),
    ],
)
def test_cli_live_http_local_media_cover_timecodes_and_single_player(
    tmp_path,
    settings,
    live_server,
    content_type,
    filename,
    signature,
    player_tag,
):
    settings.MEDIA_ROOT = tmp_path / f"media-{content_type}"
    key = ApiKey.objects.create(
        name=f"Remote {content_type} reviewer",
        token=content_type[0] * 43,
    )
    (tmp_path / "cover.png").write_bytes(_png_bytes("purple"))
    (tmp_path / filename).write_bytes(signature)
    note = tmp_path / f"{content_type}.md"
    note.write_text(
        "---\n"
        f"title: Remote {content_type.title()} E2E\n"
        f"description: Local {content_type} review\n"
        f"content_type: {content_type}\n"
        f"media_url: {filename}\n"
        "cover: cover.png\n"
        "---\n"
        "Before primary.\n\n"
        f"![[{filename}]]\n\n"
        "```timecodes\n0:00 Intro\n1:23 Main section\n```\n",
        encoding="utf-8",
    )

    result = _publish(note, live_server, key.token)
    post = Post.objects.get(slug=result["slug"])
    assert post.content_type == content_type
    assert post.media_url == ""
    assert post.primary_media.original_filename == filename
    assert post.cover_media.original_filename == "cover.png"
    assert post.timecodes == [
        {"time": "0:00", "seconds": 0, "label": "Intro"},
        {"time": "1:23", "seconds": 83, "label": "Main section"},
    ]
    assert filename not in post.content
    assert AuditLog.objects.filter(post=post, api_key=key).count() == 1

    public = Client()
    listing = public.get("/")
    detail = public.get(post.get_absolute_url())
    assert listing.status_code == detail.status_code == 200
    document = detail.content.decode()
    assert document.count(f"<{player_tag}") == 1
    body_match = re.search(
        r'<div class="post-content markdown-content">(.*?)</div>',
        document,
        re.DOTALL,
    )
    assert body_match
    assert not re.search(rf'<{player_tag}\b', body_match.group(1))
    assert document.count('class="timecode-button"') == 2
    assert post.player_media_url in document


@pytest.mark.django_db
def test_social_image_preserves_absolute_storage_url(tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    post = Post.objects.create(
        title="Absolute storage cover",
        description="S3-compatible social URL",
        content="Body",
        slug="absolute-storage-cover",
        status=Post.Status.PUBLISHED,
    )
    cover = PostMedia.objects.create(
        post=post,
        file="posts/absolute-storage-cover/cover.png",
        original_filename="cover.png",
    )
    storage = cover.file.storage
    monkeypatch.setattr(
        storage,
        "url",
        lambda name: f"https://cdn.example/{name}",
    )

    with override_settings(ALLOWED_HOSTS=["blog.example"]):
        response = Client().get(
            post.get_absolute_url(),
            secure=True,
            HTTP_HOST="blog.example",
        )
    document = response.content.decode()
    meta = _meta(document)
    assert response.status_code == 200
    assert meta["og:image"].startswith("https://cdn.example/")
    assert "blog.examplehttps://" not in document
