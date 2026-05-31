"""Tests for development media serving behavior."""

from __future__ import annotations

import pytest

from blog.dev_media import serve_media_with_range


@pytest.mark.django_db
def test_dev_media_view_supports_http_range_requests(tmp_path, rf):
    media_file = tmp_path / "demo.mp4"
    media_file.write_bytes(b"0123456789")
    request = rf.get("/media/demo.mp4", HTTP_RANGE="bytes=2-5")

    response = serve_media_with_range(request, "demo.mp4", tmp_path)

    assert response.status_code == 206
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Range"] == "bytes 2-5/10"
    assert response.headers["Content-Length"] == "4"
    assert b"".join(response.streaming_content) == b"2345"


def test_dev_media_view_advertises_range_support_for_full_response(tmp_path, rf):
    media_file = tmp_path / "demo.opus"
    media_file.write_bytes(b"abcdef")
    request = rf.get("/media/demo.opus")

    response = serve_media_with_range(request, "demo.opus", tmp_path)

    assert response.status_code == 200
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Length"] == "6"
