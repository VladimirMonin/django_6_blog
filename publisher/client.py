"""HTTP client for the blog publish API.

Uses ``urllib`` from the standard library — zero external dependencies.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class ApiError(Exception):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, body: dict[str, Any]):
        self.status_code = status_code
        self.body = body
        message = body.get("error") or json.dumps(body.get("errors", body))
        super().__init__(f"API returned {status_code}: {message}")


def publish_post(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    replace: bool = False,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Send a POST request to the publish API endpoint.

    Args:
        url: Base URL of the blog (e.g. ``http://127.0.0.1:8036``).
        api_key: Bearer token for authentication.
        payload: JSON-serializable post payload from ``parse_markdown_file``.
        replace: If True, add ``replace=True`` to payload to overwrite existing.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response body (serialized post).

    Raises:
        ApiError: On non-2xx API response.
        urllib.error.URLError: On connection failure.
    """
    if replace:
        payload = {**payload, "replace": True}

    endpoint = url.rstrip("/") + "/api/v1/posts/publish/"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_body = {"error": str(exc)}
        raise ApiError(exc.code, error_body) from exc