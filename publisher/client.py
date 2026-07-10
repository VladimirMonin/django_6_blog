"""Zero-dependency HTTP client for the blog publishing APIs."""

from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator


class ApiError(Exception):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, body: dict[str, Any]):
        self.status_code = status_code
        self.body = body
        message = body.get("error") or json.dumps(body.get("errors", body))
        super().__init__(f"API returned {status_code}: {message}")


def _open_json(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_body = {"error": f"HTTP {exc.code}"}
        raise ApiError(exc.code, error_body) from exc


def publish_post(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    replace: bool = False,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Send a JSON request to the backward-compatible publish endpoint."""
    if replace:
        payload = {**payload, "replace": True}
    endpoint = url.rstrip("/") + "/api/v1/posts/publish/"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    return _open_json(request, timeout)


class MultipartBody:
    """Replayable streaming multipart body with a known Content-Length."""

    def __init__(self, manifest: dict[str, Any], files: dict[str, Path]):
        self.boundary = "publisher-" + secrets.token_hex(16)
        self.manifest = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.files = files
        self._manifest_prefix = self._part_header("manifest", content_type="application/json; charset=utf-8")
        self._file_headers = {
            part: self._part_header(
                part,
                filename=path.name,
                content_type="application/octet-stream",
            )
            for part, path in files.items()
        }
        self._closing = f"--{self.boundary}--\r\n".encode()
        self.content_length = (
            len(self._manifest_prefix) + len(self.manifest) + 2
            + sum(len(self._file_headers[part]) + path.stat().st_size + 2 for part, path in files.items())
            + len(self._closing)
        )

    def _part_header(self, name: str, *, filename: str | None = None, content_type: str) -> bytes:
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            safe_name = filename.replace('"', "")
            disposition += f'; filename="{safe_name}"'
        return (
            f"--{self.boundary}\r\n{disposition}\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")

    def __iter__(self) -> Iterator[bytes]:
        yield self._manifest_prefix
        yield self.manifest
        yield b"\r\n"
        for part, path in self.files.items():
            yield self._file_headers[part]
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    yield chunk
            yield b"\r\n"
        yield self._closing


def publish_package(
    *,
    url: str,
    api_key: str,
    manifest: dict[str, Any],
    files: dict[str, Path],
    idempotency_key: str,
    timeout: float = 120.0,
    retries: int = 1,
    retry_delay: float = 0.25,
) -> dict[str, Any]:
    """Stream a manifest and files, retrying transport failures safely."""
    body = MultipartBody(manifest, files)
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url.rstrip("/") + "/api/v1/posts/publish-package/",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Idempotency-Key": idempotency_key,
                "Content-Type": f"multipart/form-data; boundary={body.boundary}",
                "Content-Length": str(body.content_length),
            },
        )
        try:
            return _open_json(request, timeout)
        except (urllib.error.URLError, TimeoutError):
            if attempt >= retries:
                raise
            if retry_delay:
                time.sleep(retry_delay)
    raise RuntimeError("unreachable")
