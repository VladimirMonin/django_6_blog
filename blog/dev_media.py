"""Development-only media serving helpers with HTTP Range support."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import http_date
from django.utils._os import safe_join

_RANGE_RE = re.compile(r"bytes=(?P<start>\d*)-(?P<end>\d*)")
_CHUNK_SIZE = 8192


def _iter_file_range(path: Path, start: int, end: int):
    remaining = end - start + 1
    with path.open("rb") as file_obj:
        file_obj.seek(start)
        while remaining > 0:
            chunk = file_obj.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def serve_media_with_range(request, path: str, document_root: str | Path):
    """Serve a local media file in DEBUG mode, honoring single byte ranges.

    Django's built-in development static helper does not advertise byte-range
    support. Browser audio/video seeking relies on this for realistic local
    playback checks, so this view implements the small subset needed for media
    files while keeping path traversal protection via ``safe_join``.
    """

    try:
        full_path = Path(safe_join(document_root, path))
    except ValueError as exc:
        raise Http404("Media path is outside MEDIA_ROOT") from exc

    if not full_path.exists() or not full_path.is_file():
        raise Http404("Media file not found")

    file_size = full_path.stat().st_size
    content_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{full_path.name}"',
        "Last-Modified": http_date(full_path.stat().st_mtime),
    }

    range_header = request.headers.get("Range", "")
    match = _RANGE_RE.fullmatch(range_header.strip()) if range_header else None
    if not match:
        response = FileResponse(full_path.open("rb"), content_type=content_type)
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        response.headers["Content-Length"] = str(file_size)
        return response

    start_text = match.group("start")
    end_text = match.group("end")
    if not start_text and not end_text:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    if start_text:
        start = int(start_text)
        end = int(end_text) if end_text else file_size - 1
    else:
        suffix_length = int(end_text)
        if suffix_length == 0:
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})
        start = max(file_size - suffix_length, 0)
        end = file_size - 1

    if start >= file_size or end < start:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    end = min(end, file_size - 1)
    content_length = end - start + 1
    response = StreamingHttpResponse(
        _iter_file_range(full_path, start, end),
        status=206,
        content_type=content_type,
    )
    for header_name, header_value in headers.items():
        response.headers[header_name] = header_value
    response.headers["Content-Length"] = str(content_length)
    response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return response
