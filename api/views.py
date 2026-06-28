"""API views for post management."""

import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from blog.models import Category, Post, Tag
from blog.slug_utils import build_slug

from .decorators import require_api_key
from .serializers import serialize_post


@csrf_exempt
@require_POST
@require_api_key
def publish_post(request):
    """Create or replace a blog post from JSON payload."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    content = data.get("content") or ""

    errors = []
    if not title:
        errors.append("title is required")
    if not description:
        errors.append("description is required")
    if not content:
        errors.append("content is required")
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    content_type = (data.get("content_type") or "article").strip().casefold()
    media_url = (data.get("media_url") or "").strip()
    status = data.get("status", "published")
    if status not in ("published", "draft"):
        status = "published"
    status_value = Post.Status.DRAFT if status == "draft" else Post.Status.PUBLISHED

    slug = (data.get("slug") or "").strip() or build_slug(title, fallback="post")
    replace = bool(data.get("replace", False))

    existing = Post.objects.filter(slug=slug)
    if existing.exists() and not replace:
        return JsonResponse(
            {"error": f"Post with slug '{slug}' already exists. Use replace=true to overwrite."},
            status=409,
        )
    if replace and existing.exists():
        existing.delete()

    category_name = (data.get("category") or "").strip()
    category = None
    if category_name:
        category = Category.objects.get_or_create(name=category_name)[0]

    timecodes = data.get("timecodes") or []
    if isinstance(timecodes, list):
        parsed_timecodes = []
        for tc in timecodes:
            if isinstance(tc, dict) and "time" in tc and "label" in tc:
                parsed_timecodes.append({
                    "time": tc["time"],
                    "seconds": _parse_time_to_seconds(tc["time"]),
                    "label": tc["label"],
                })
        timecodes = parsed_timecodes
    else:
        timecodes = []

    type_aliases = {
        "article": Post.ContentType.ARTICLE,
        "video": Post.ContentType.VIDEO,
        "audio": Post.ContentType.AUDIO,
        "podcast": Post.ContentType.PODCAST,
    }
    content_type_value = type_aliases.get(content_type, Post.ContentType.ARTICLE)

    with transaction.atomic():
        post = Post.objects.create(
            title=title,
            description=description,
            slug=slug,
            content=content,
            content_type=content_type_value,
            media_url=media_url,
            timecodes=timecodes,
            status=status_value,
            category=category,
        )

        tag_names = data.get("tags") or []
        if isinstance(tag_names, list):
            for tag_name in tag_names:
                tag = Tag.objects.get_or_create(name=tag_name)[0]
                post.tags.add(tag)

    return JsonResponse(serialize_post(post), status=201)


def _parse_time_to_seconds(time_str: str) -> int:
    """Parse 'M:SS' or 'H:MM:SS' to seconds."""
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0