"""API authentication decorator."""

import json

from django.http import JsonResponse

from .models import ApiKey


def require_api_key(view_func):
    """Require a valid API key in Authorization: Bearer <token> header."""

    def wrapper(request, *args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JsonResponse(
                {"error": "Missing or invalid Authorization header"},
                status=401,
            )
        token = auth[7:].strip()
        api_key = ApiKey.verify(token)
        if not api_key:
            return JsonResponse(
                {"error": "Invalid or revoked API key"},
                status=401,
            )
        request.api_key = api_key
        return view_func(request, *args, **kwargs)

    return wrapper