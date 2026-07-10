"""Focused tests for the standalone Publisher local-asset package path."""

import json
import os
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

from publisher.client import ApiError, publish_package
from publisher.package import build_publish_package
from publisher.parser import parse_markdown_file


def _note(tmp_path: Path, body: str, *, name: str = "note.md") -> Path:
    note = tmp_path / name
    note.write_text(body, encoding="utf-8")
    return note


def _asset_by_name(manifest: dict, name: str) -> dict:
    return next(asset for asset in manifest["assets"] if asset["original_filename"] == name)


def test_discovers_body_image_and_cover_once(tmp_path):
    (tmp_path / "images").mkdir()
    image = tmp_path / "images" / "cover.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nimage")
    note = _note(
        tmp_path,
        "---\ntitle: Assets\ndescription: local files\ncover: images/cover.png\n---\n"
        "Body\n\n![[images/cover.png|640]]\n",
    )

    manifest, files, key = build_publish_package(note, parse_markdown_file(note))

    assert len(manifest["assets"]) == 1
    asset = manifest["assets"][0]
    assert asset["source_refs"] == ["images/cover.png"]
    assert asset["roles"] == ["body", "cover"]
    assert files[asset["part"]] == image.resolve()
    assert key == manifest["package_sha256"]
    assert str(tmp_path) not in json.dumps(manifest)


@pytest.mark.parametrize(
    ("content_type", "filename", "data"),
    [
        ("video", "clip.mp4", b"\x00\x00\x00\x18ftypisom"),
        ("podcast", "episode.opus", b"OggSepisode"),
    ],
)
def test_local_media_url_becomes_primary_upload(tmp_path, content_type, filename, data):
    (tmp_path / filename).write_bytes(data)
    note = _note(
        tmp_path,
        f"---\ndescription: media\ncontent_type: {content_type}\nmedia_url: {filename}\n---\nBody\n",
    )

    manifest, files, _ = build_publish_package(note, parse_markdown_file(note))

    asset = _asset_by_name(manifest, filename)
    assert asset["roles"] == ["primary"]
    assert "media_url" not in manifest["post"]
    assert list(files.values()) == [(tmp_path / filename).resolve()]


def test_external_media_url_stays_json_compatible(tmp_path):
    note = _note(
        tmp_path,
        "---\ndescription: remote\ncontent_type: video\nmedia_url: https://cdn.example/video.mp4\n---\nBody\n",
    )
    payload = parse_markdown_file(note)

    manifest, files, _ = build_publish_package(note, payload)

    assert files == {}
    assert manifest["post"]["media_url"] == "https://cdn.example/video.mp4"


def test_non_http_media_url_is_not_treated_as_external(tmp_path):
    note = _note(
        tmp_path,
        "---\ndescription: unsafe\ncontent_type: video\nmedia_url: file:///etc/passwd\n---\nBody\n",
    )
    with pytest.raises(ValueError, match="inside --assets-dir"):
        build_publish_package(note, parse_markdown_file(note))


def test_explicit_assets_dir_resolves_logical_refs_without_exposing_root(tmp_path):
    notes = tmp_path / "notes"
    assets = tmp_path / "vault-assets"
    notes.mkdir()
    (assets / "images").mkdir(parents=True)
    image = assets / "images" / "diagram.webp"
    image.write_bytes(b"RIFFxxxxWEBPdata")
    note = _note(
        notes,
        "---\ndescription: explicit root\n---\n![Diagram](images/diagram.webp)\n",
    )

    manifest, files, _ = build_publish_package(
        note,
        parse_markdown_file(note),
        assets_dir=assets,
    )

    assert manifest["assets"][0]["source_refs"] == ["images/diagram.webp"]
    assert list(files.values()) == [image.resolve()]
    assert str(assets) not in json.dumps(manifest)


def test_external_primary_cannot_be_combined_with_local_player(tmp_path):
    (tmp_path / "other.opus").write_bytes(b"OggSother")
    note = _note(
        tmp_path,
        "---\ndescription: conflict\ncontent_type: podcast\n"
        "media_url: https://cdn.example/episode.opus\n---\n![[other.opus]]\n",
    )

    with pytest.raises(ValueError, match="cannot combine"):
        build_publish_package(note, parse_markdown_file(note))


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("missing.png", "missing"),
        ("../outside.png", "inside --assets-dir"),
        ("/tmp/outside.png", "inside --assets-dir"),
    ],
)
def test_rejects_missing_and_outside_references_before_network(tmp_path, reference, message):
    note = _note(tmp_path, f"---\ndescription: unsafe\n---\n![[{reference}]]\n")
    with pytest.raises(ValueError, match=message):
        build_publish_package(note, parse_markdown_file(note))


def test_rejects_symlink_escape_and_duplicate_normalized_basenames(tmp_path):
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "escape.png").symlink_to(outside)
    escaped = _note(tmp_path, "---\ndescription: link\n---\n![[escape.png]]\n")
    with pytest.raises(ValueError, match="escapes"):
        build_publish_package(escaped, parse_markdown_file(escaped))

    for directory in ("one", "two"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "same.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    duplicate = _note(
        tmp_path,
        "---\ndescription: duplicate\n---\n![[one/same.png]]\n![[two/same.png]]\n",
    )
    with pytest.raises(ValueError, match="Duplicate normalized"):
        build_publish_package(duplicate, parse_markdown_file(duplicate))


def test_rejects_non_image_cover_and_empty_asset(tmp_path):
    (tmp_path / "cover.opus").write_bytes(b"OggS")
    bad_cover = _note(
        tmp_path,
        "---\ndescription: cover\ncover: cover.opus\n---\nBody\n",
    )
    with pytest.raises(ValueError, match="Cover must be an image"):
        build_publish_package(bad_cover, parse_markdown_file(bad_cover))

    (tmp_path / "empty.png").write_bytes(b"")
    empty = _note(tmp_path, "---\ndescription: empty\n---\n![[empty.png]]\n")
    with pytest.raises(ValueError, match="empty"):
        build_publish_package(empty, parse_markdown_file(empty))


def test_publish_package_retries_transport_failure_with_same_body(tmp_path, monkeypatch):
    asset = tmp_path / "image.png"
    asset.write_bytes(b"\x89PNG\r\n\x1a\nimage")
    manifest = {"protocol_version": 1, "post": {"title": "T"}, "assets": []}
    seen_bodies = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"slug":"ok"}'

    def fake_urlopen(request, timeout):
        seen_bodies.append(b"".join(request.data))
        if len(seen_bodies) == 1:
            raise urllib.error.URLError("temporary")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = publish_package(
        url="https://blog.example",
        api_key="secret-token",
        manifest=manifest,
        files={"asset_a001": asset},
        idempotency_key="deterministic-key",
        retries=1,
        retry_delay=0,
    )

    assert result == {"slug": "ok"}
    assert len(seen_bodies) == 2
    assert seen_bodies[0] == seen_bodies[1]
    assert b"secret-token" not in seen_bodies[0]


def test_publish_package_does_not_retry_api_error(tmp_path, monkeypatch):
    asset = tmp_path / "image.png"
    asset.write_bytes(b"png")
    calls = 0

    def fake_open_json(request, timeout):
        nonlocal calls
        calls += 1
        raise ApiError(400, {"error": "invalid package"})

    monkeypatch.setattr("publisher.client._open_json", fake_open_json)
    with pytest.raises(ApiError, match="invalid package"):
        publish_package(
            url="https://blog.example",
            api_key="secret-token",
            manifest={"protocol_version": 1},
            files={"asset_a001": asset},
            idempotency_key="deterministic-key",
            retries=3,
            retry_delay=0,
        )
    assert calls == 1


def test_cli_asset_dry_run_is_redacted_and_uses_env_without_requiring_network(tmp_path):
    image = tmp_path / "private-image.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nprivate-binary-marker")
    note = _note(tmp_path, "---\ndescription: dry package\n---\n![[private-image.png]]\n")
    token = "TOP-SECRET-PUBLISHER-TOKEN"
    env = {**os.environ, "BLOG_API_KEY": token, "BLOG_API_URL": "https://blog.example"}

    result = subprocess.run(
        [sys.executable, "-m", "publisher", "publish", str(note), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    manifest = output["manifest"]
    assert manifest["assets"][0]["original_filename"] == image.name
    assert output["validation"] == {
        "asset_count": 1,
        "total_bytes": image.stat().st_size,
        "idempotency_key": manifest["package_sha256"],
    }
    assert token not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr
    assert "private-binary-marker" not in result.stdout


def test_cli_asset_error_precedes_network_and_does_not_leak_key(tmp_path):
    note = _note(tmp_path, "---\ndescription: missing\n---\n![[missing.png]]\n")
    token = "TOP-SECRET-PUBLISHER-TOKEN"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "publisher",
            "publish",
            str(note),
            "--url",
            "https://unreachable.invalid",
            "--key",
            token,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "Asset error" in result.stderr
    assert "missing.png" in result.stderr
    assert token not in result.stdout + result.stderr
