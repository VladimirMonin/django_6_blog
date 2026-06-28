"""Response serialization helpers for API endpoints."""

from blog.models import Post


def serialize_post(post: Post) -> dict:
    """Serialize a Post to a JSON-compatible dict."""
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
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }