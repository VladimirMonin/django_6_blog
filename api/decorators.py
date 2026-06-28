"""API authentication decorator with rate limiting."""

import time
from collections import defaultdict
from collections import deque

from django.http import JsonResponse

from .models import ApiKey

# In-memory rate-limit state: token -> deque of request timestamps.
# 60 requests per 60-second sliding window per API key.
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 60  # requests
_rate_buckets: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(token: str) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds) for the given token.

    Uses a sliding-window counter: keeps timestamps of the last
    _RATE_LIMIT_MAX requests; if the oldest is within the window,
    the limit is exceeded.
    """
    now = time.monotonic()
    bucket = _rate_buckets[token]

    # Evict timestamps older than the window
    cutoff = now - _RATE_LIMIT_WINDOW
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()

    if len(bucket) >= _RATE_LIMIT_MAX:
        # Calculate retry_after: time until the oldest request ages out
        retry_after = int(bucket[0] + _RATE_LIMIT_WINDOW - now) + 1
        return False, max(retry_after, 1)

    bucket.append(now)
    return True, 0


def _reset_rate_limit() -> None:
    """Clear all rate-limit buckets (for testing)."""
    _rate_buckets.clear()


def require_api_key(permission: str = "read"):
    """Require a valid API key with the given permission in Authorization: Bearer *** header.

    Enforces a per-key rate limit of 60 requests per minute.

    Usage:
        @require_api_key("publish")
        def my_view(request): ...
    """

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return JsonResponse(
                    {"error": "Missing or invalid Authorization header"},
                    status=401,
                )
            token = auth[7:].strip()

            # Rate limit check before DB lookup
            allowed, retry_after = _check_rate_limit(token)
            if not allowed:
                return JsonResponse(
                    {"error": "Rate limit exceeded", "retry_after": retry_after},
                    status=429,
                )

            api_key = ApiKey.verify(token)
            if not api_key:
                return JsonResponse(
                    {"error": "Invalid, revoked or expired API key"},
                    status=401,
                )
            if not api_key.has_permission(permission):
                return JsonResponse(
                    {"error": f"API key lacks required permission: {permission}"},
                    status=403,
                )
            request.api_key = api_key
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator