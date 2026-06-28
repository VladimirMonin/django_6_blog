"""API views for post management."""

import json
import logging
import re

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from blog.models import AuditLog, Category, Post, PostView, Series, Tag
from blog.slug_utils import build_slug

from .decorators import require_api_key
from .serializers import serialize_post, serialize_post_list_item

logger = logging.getLogger("api.views")

APP_VERSION = "1.0"

# Valid sort fields for list_posts
VALID_SORT_FIELDS = {
    "created_at",
    "-created_at",
    "title",
    "-title",
    "view_count",
    "-view_count",
    "published_at",
    "-published_at",
}

# Timecode format: M:SS, MM:SS, H:MM:SS, HH:MM:SS
_TIMECODE_RE = re.compile(r"^\d{1,2}:[0-5]\d(?::[0-5]\d)?$")


@csrf_exempt
@require_GET
def health(request):
    """Public health check endpoint — no API key required."""
    try:
        post_count = Post.objects.filter(deleted_at__isnull=True).count()
        db_status = "ok"
    except Exception:
        post_count = 0
        db_status = "error"

    return JsonResponse(
        {
            "status": "ok",
            "db": db_status,
            "post_count": post_count,
            "version": APP_VERSION,
        }
    )


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


def _validate_timecodes(timecodes: list) -> list[str]:
    """Validate timecode entries. Returns list of error strings (empty if valid)."""
    errors = []
    for i, tc in enumerate(timecodes, start=1):
        if not isinstance(tc, dict):
            errors.append(f"timecode #{i}: must be an object")
            continue
        time_val = tc.get("time")
        label = tc.get("label")
        if not isinstance(time_val, str) or not time_val.strip():
            errors.append(f"timecode #{i}: 'time' is required and must be a string")
            continue
        if not _TIMECODE_RE.match(time_val.strip()):
            errors.append(
                f"timecode #{i}: invalid time format '{time_val}'. "
                "Expected M:SS, MM:SS, or H:MM:SS"
            )
            continue
        if not isinstance(label, str) or not label.strip():
            errors.append(f"timecode #{i}: 'label' is required and must be a non-empty string")
    return errors


def _validate_post_payload(data: dict) -> list[str]:
    """Validate required fields and content-type-specific requirements.

    Returns list of error strings (empty if valid).
    """
    errors = []
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    content = data.get("content") or ""

    if not title:
        errors.append("title is required")
    if not description:
        errors.append("description is required")
    if not content:
        errors.append("content is required")

    content_type = (data.get("content_type") or "article").strip().casefold()
    media_url = (data.get("media_url") or "").strip()

    # media_url required for video/audio/podcast
    if content_type in ("video", "audio", "podcast") and not media_url:
        errors.append(f"media_url is required for content_type '{content_type}'")

    # Validate timecodes format strictly
    timecodes = data.get("timecodes") or []
    if isinstance(timecodes, list) and timecodes:
        tc_errors = _validate_timecodes(timecodes)
        errors.extend(tc_errors)

    return errors


@csrf_exempt
@require_POST
@require_api_key("publish")
def publish_post(request):
    """Create or replace a blog post from JSON payload."""
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    errors = _validate_post_payload(data)
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    content = data.get("content") or ""

    content_type = (data.get("content_type") or "article").strip().casefold()
    media_url = (data.get("media_url") or "").strip()
    status = data.get("status", "published")
    if status not in ("published", "draft"):
        status = "published"
    status_value = Post.Status.DRAFT if status == "draft" else Post.Status.PUBLISHED

    slug = (data.get("slug") or "").strip() or build_slug(title, fallback="post")
    replace = bool(data.get("replace", False))
    source_id = (data.get("source_id") or "").strip() or None

    # Idempotent publish: if source_id matches existing post, update it
    if source_id:
        existing_by_source = Post.objects.filter(source_id=source_id, deleted_at__isnull=True).first()
        if existing_by_source:
            replace = True
            slug = existing_by_source.slug

    existing = Post.objects.filter(slug=slug, deleted_at__isnull=True)
    if existing.exists() and not replace:
        return JsonResponse(
            {"error": f"Post with slug '{slug}' already exists. Use replace=true to overwrite."},
            status=409,
        )
    if replace and existing.exists():
        existing.first().hard_delete()

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
            source_id=source_id,
        )

        tag_names = data.get("tags") or []
        if isinstance(tag_names, list):
            for tag_name in tag_names:
                tag = Tag.objects.get_or_create(name=tag_name)[0]
                post.tags.add(tag)

    AuditLog.log(
        action=AuditLog.Action.PUBLISHED,
        post=post,
        api_key=getattr(request, "api_key", None),
        detail={"source_id": source_id, "content_type": content_type_value},
    )
    logger.info(
        "api.action",
        extra={
            "action": AuditLog.Action.PUBLISHED,
            "post_slug": post.slug,
            "api_key": getattr(getattr(request, "api_key", None), "name", None),
        },
    )

    return JsonResponse(serialize_post(post), status=201)


@csrf_exempt
@require_api_key("publish")
def bulk_publish(request):
    """Publish multiple posts in a single request.

    Accepts: {"posts": [{...}, {...}]}
    Returns: {"results": [{...}, ...], "created": N, "errors": [...]}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    posts_data = data.get("posts")
    if not isinstance(posts_data, list):
        return JsonResponse({"error": "Expected 'posts' array"}, status=400)

    if not posts_data:
        return JsonResponse({"error": "posts array is empty"}, status=400)

    results = []
    errors = []
    created = 0

    for index, post_data in enumerate(posts_data):
        if not isinstance(post_data, dict):
            errors.append({"index": index, "error": "post must be an object"})
            results.append({"index": index, "success": False, "error": "post must be an object"})
            continue

        # Validate each post
        validation_errors = _validate_post_payload(post_data)
        if validation_errors:
            errors.append({"index": index, "errors": validation_errors})
            results.append({"index": index, "success": False, "errors": validation_errors})
            continue

        # Build the post using the same logic as publish_post
        title = (post_data.get("title") or "").strip()
        description = (post_data.get("description") or "").strip()
        content = post_data.get("content") or ""
        content_type = (post_data.get("content_type") or "article").strip().casefold()
        media_url = (post_data.get("media_url") or "").strip()
        post_status = post_data.get("status", "published")
        if post_status not in ("published", "draft"):
            post_status = "published"
        status_value = Post.Status.DRAFT if post_status == "draft" else Post.Status.PUBLISHED

        slug = (post_data.get("slug") or "").strip() or build_slug(title, fallback=f"post-{index}")
        replace = bool(post_data.get("replace", False))
        source_id = (post_data.get("source_id") or "").strip() or None

        if source_id:
            existing_by_source = Post.objects.filter(
                source_id=source_id, deleted_at__isnull=True
            ).first()
            if existing_by_source:
                replace = True
                slug = existing_by_source.slug

        existing = Post.objects.filter(slug=slug, deleted_at__isnull=True)
        if existing.exists() and not replace:
            errors.append({"index": index, "error": f"slug '{slug}' already exists"})
            results.append(
                {"index": index, "success": False, "error": f"slug '{slug}' already exists"}
            )
            continue
        if replace and existing.exists():
            existing.first().hard_delete()

        category_name = (post_data.get("category") or "").strip()
        category = (
            Category.objects.get_or_create(name=category_name)[0] if category_name else None
        )

        series_name = (post_data.get("series") or "").strip()
        series = Series.objects.get_or_create(name=series_name)[0] if series_name else None
        series_order = int(post_data.get("series_order", 0) or 0)

        timecodes = post_data.get("timecodes") or []
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

        try:
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
                    source_id=source_id,
                )

                tag_names = post_data.get("tags") or []
                if isinstance(tag_names, list):
                    for tag_name in tag_names:
                        tag = Tag.objects.get_or_create(name=tag_name)[0]
                        post.tags.add(tag)

            AuditLog.log(
                action=AuditLog.Action.PUBLISHED,
                post=post,
                api_key=getattr(request, "api_key", None),
                detail={"source_id": source_id, "content_type": content_type_value, "bulk": True},
            )
            logger.info(
                "api.action",
                extra={
                    "action": AuditLog.Action.PUBLISHED,
                    "post_slug": post.slug,
                    "api_key": getattr(getattr(request, "api_key", None), "name", None),
                },
            )
            created += 1
            results.append(
                {"index": index, "success": True, "slug": post.slug, "id": post.pk}
            )
        except Exception as exc:
            errors.append({"index": index, "error": str(exc)})
            results.append({"index": index, "success": False, "error": str(exc)})

    return JsonResponse(
        {"results": results, "created": created, "errors": errors},
        status=201 if created > 0 else 400,
    )


@csrf_exempt
@require_api_key("read")
def list_posts(request):
    """List posts for agents with filters, sorting, and pagination."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    posts = (
        Post.objects.filter(deleted_at__isnull=True)
        .select_related("category", "series")
        .prefetch_related("tags")
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

    # Sort parameter
    sort = (request.GET.get("sort") or "-created_at").strip()
    if sort not in VALID_SORT_FIELDS:
        return JsonResponse(
            {"error": f"Invalid sort field '{sort}'. Valid values: {', '.join(sorted(VALID_SORT_FIELDS))}"},
            status=400,
        )
    posts = posts.order_by(sort)

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
@require_api_key("delete")
def post_detail_api(request, slug: str):
    """Retrieve or delete a single post by slug."""
    post = (
        Post.objects.filter(slug=slug, deleted_at__isnull=True)
        .select_related("category", "series")
        .prefetch_related("tags")
        .first()
    )
    if not post:
        return JsonResponse({"error": "Post not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(serialize_post(post))

    if request.method == "DELETE":
        old_status = post.status
        post.soft_delete()
        AuditLog.log(
            action=AuditLog.Action.DELETED,
            post=post,
            api_key=getattr(request, "api_key", None),
            detail={"old_status": old_status, "slug": post.slug},
        )
        logger.info(
            "api.action",
            extra={
                "action": AuditLog.Action.DELETED,
                "post_slug": post.slug,
                "api_key": getattr(getattr(request, "api_key", None), "name", None),
            },
        )
        return JsonResponse({}, status=204)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_api_key("status")
def update_post_status(request, slug: str):
    """Change post status between published and draft."""
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    post = Post.objects.filter(slug=slug, deleted_at__isnull=True).first()
    if not post:
        return JsonResponse({"error": "Post not found"}, status=404)

    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    status = data.get("status")
    if status not in {Post.Status.PUBLISHED, Post.Status.DRAFT, Post.Status.ARCHIVED}:
        return JsonResponse(
            {"error": "status must be 'published', 'draft' or 'archived'"}, status=400
        )

    old_status = post.status
    post.status = status
    if status == Post.Status.PUBLISHED and not post.published_at:
        post.published_at = timezone.now()
    post.save(update_fields=["status", "published_at", "updated_at"])
    post.refresh_from_db()
    AuditLog.log(
        action=AuditLog.Action.STATUS_CHANGED,
        post=post,
        api_key=getattr(request, "api_key", None),
        detail={"old_status": old_status, "new_status": status},
    )
    return JsonResponse(serialize_post(post))


@csrf_exempt
@require_api_key("stats")
def stats(request):
    """Return aggregate statistics about posts."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    active_posts = Post.objects.filter(deleted_at__isnull=True)

    # Total posts by status
    by_status = {}
    for choice_value, _label in Post.Status.choices:
        by_status[choice_value] = active_posts.filter(status=choice_value).count()

    # Total by content_type
    by_content_type = {}
    for choice_value, _label in Post.ContentType.choices:
        by_content_type[choice_value] = active_posts.filter(content_type=choice_value).count()

    # Total by category (top 5)
    by_category = list(
        active_posts.filter(category__isnull=False)
        .values("category__name")
        .annotate(count=Count("pk"))
        .order_by("-count")[:5]
    )
    by_category = {item["category__name"]: item["count"] for item in by_category}

    # Total views and likes
    totals = active_posts.aggregate(
        total_views=Sum("view_count"),
        total_likes=Sum("like_count"),
    )

    # Featured count
    featured_count = active_posts.filter(is_featured=True).count()

    return JsonResponse(
        {
            "by_status": by_status,
            "by_content_type": by_content_type,
            "by_category": by_category,
            "total_views": totals["total_views"] or 0,
            "total_likes": totals["total_likes"] or 0,
            "featured_count": featured_count,
        }
    )


@csrf_exempt
def read_depth(request, slug: str):
    """Public endpoint for read-depth tracking — no API key required.

    Accepts POST with {read_depth: 0.0-1.0} from the browser JS tracker.
    Creates a PostView record for analytics.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    post = Post.objects.filter(slug=slug, deleted_at__isnull=True, status=Post.Status.PUBLISHED).first()
    if not post:
        return JsonResponse({"error": "Post not found"}, status=404)

    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    read_depth_value = data.get("read_depth", 0)
    try:
        read_depth_value = max(0.0, min(1.0, float(read_depth_value)))
    except (TypeError, ValueError):
        read_depth_value = 0.0

    session_key = ""
    if hasattr(request, "session"):
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key or ""

    PostView.objects.create(
        post=post,
        session_key=session_key,
        read_depth=read_depth_value,
    )

    return JsonResponse({"ok": True}, status=201)