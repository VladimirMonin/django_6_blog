"""API views for post management."""

import json

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from blog.models import Category, Post, Series, Tag
from blog.slug_utils import build_slug

from .decorators import require_api_key
from .serializers import serialize_post, serialize_post_list_item


def _parse_json_body(request: HttpRequest):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def _parse_time_to_seconds(time_str: str) -> int:
    """Parse 'M:SS' or 'H:MM:SS' to seconds."""
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


@csrf_exempt
@require_POST
@require_api_key
def publish_post(request):
    """Create or replace a blog post from JSON payload."""
    data = _parse_json_body(request)
    if data is None:
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
    category = Category.objects.get_or_create(name=category_name)[0] if category_name else None

    series_name = (data.get("series") or "").strip()
    series = Series.objects.get_or_create(name=series_name)[0] if series_name else None
    series_order = int(data.get("series_order", 0) or 0)

    timecodes = data.get("timecodes") or []
    if isinstance(timecodes, list):
        parsed_timecodes = []
        for tc in timecodes:
            if isinstance(tc, dict) and "time" in tc and "label" in tc:
                parsed_timecodes.append(
                    {
                        "time": tc["time"],
                        "seconds": _parse_time_to_seconds(tc["time"]),
                        "label": tc["label"],
                    }
                )
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
            series=series,
            series_order=series_order,
        )

        tag_names = data.get("tags") or []
        if isinstance(tag_names, list):
            for tag_name in tag_names:
                tag = Tag.objects.get_or_create(name=tag_name)[0]
                post.tags.add(tag)

    return JsonResponse(serialize_post(post), status=201)


@csrf_exempt
@require_api_key
def list_posts(request):
    """List posts for agents with filters and pagination."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    posts = (
        Post.objects.all()
        .select_related("category", "series")
        .prefetch_related("tags")
        .order_by("-created_at")
    )

    status = (request.GET.get("status") or "").strip()
    if status in {Post.Status.PUBLISHED, Post.Status.DRAFT}:
        posts = posts.filter(status=status)

    content_type = (request.GET.get("content_type") or "").strip()
    if content_type in dict(Post.ContentType.choices):
        posts = posts.filter(content_type=content_type)

    category = (request.GET.get("category") or "").strip()
    if category:
        posts = posts.filter(Q(category__slug=category) | Q(category__name=category))

    search = (request.GET.get("search") or "").strip()
    if search:
        posts = posts.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(content__icontains=search)
        )

    page = max(int(request.GET.get("page", 1) or 1), 1)
    per_page = min(max(int(request.GET.get("per_page", 20) or 20), 1), 100)
    paginator = Paginator(posts.distinct(), per_page)
    page_obj = paginator.get_page(page)

    return JsonResponse(
        {
            "results": [serialize_post_list_item(post) for post in page_obj.object_list],
            "pagination": {
                "page": page_obj.number,
                "per_page": per_page,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
            },
        }
    )


@csrf_exempt
@require_api_key
def post_detail_api(request, slug: str):
    """Retrieve or delete a single post by slug."""
    post = (
        Post.objects.filter(slug=slug)
        .select_related("category", "series")
        .prefetch_related("tags")
        .first()
    )
    if not post:
        return JsonResponse({"error": "Post not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(serialize_post(post))

    if request.method == "DELETE":
        post.delete()
        return JsonResponse({}, status=204)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_api_key
def update_post_status(request, slug: str):
    """Change post status between published and draft."""
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    post = Post.objects.filter(slug=slug).first()
    if not post:
        return JsonResponse({"error": "Post not found"}, status=404)

    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    status = data.get("status")
    if status not in {Post.Status.PUBLISHED, Post.Status.DRAFT}:
        return JsonResponse({"error": "status must be 'published' or 'draft'"}, status=400)

    post.status = status
    post.save(update_fields=["status", "updated_at"])
    post.refresh_from_db()
    return JsonResponse(serialize_post(post))
