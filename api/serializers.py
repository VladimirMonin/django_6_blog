"""Response serialization helpers for API endpoints."""

from blog.models import Post


def _base_post_dict(post: Post) -> dict:
    from django.urls import reverse

    return {
        "id": post.pk,
        "title": post.title,
        "slug": post.slug,
        "description": post.description,
        "content_type": post.content_type,
        "status": post.status,
        "media_url": post.media_url,
        "url": reverse("post_detail", kwargs={"slug": post.slug}),
        "category": post.category.name if post.category else None,
        "tags": [tag.name for tag in post.tags.all()],
        "series": post.series.name if post.series else None,
        "series_order": post.series_order if post.series else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def serialize_post(post: Post) -> dict:
    """Serialize a Post to a JSON-compatible dict."""
    return {
        **_base_post_dict(post),
        "content": post.content,
        "timecodes": post.timecodes,
    }


def serialize_post_list_item(post: Post) -> dict:
    """Compact serializer for post list endpoints."""
    return _base_post_dict(post)
