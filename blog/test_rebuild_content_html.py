"""Regression tests for targeted persisted-HTML rebuilds."""

from io import StringIO

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from blog.models import Post, PostMedia


@pytest.mark.django_db
def test_rebuild_content_html_slug_replaces_expired_media_urls_without_republishing(client):
    """A targeted rebuild is dry-run safe, updates validators, and is idempotent."""
    post = Post.objects.create(
        title="Rebuild stable media",
        description="Targeted persisted HTML rebuild",
        content="Initial body",
        slug="rebuild-stable-media",
        status=Post.Status.PUBLISHED,
    )
    media = PostMedia.objects.create(
        post=post,
        file=ContentFile(b"image-bytes", name="body.webp"),
    )
    source_markdown = "![[body.webp|Body image]]"
    post.content = source_markdown
    post.save()
    stable_url = reverse(
        "post_media", kwargs={"media_id": media.pk, "variant": "original"}
    )
    stale_url = "https://private.example.test/body.webp?X-Amz-Signature=expired"
    assert stable_url in post.content_html

    Post.objects.filter(pk=post.pk).update(
        content_html=post.content_html.replace(stable_url, stale_url)
    )
    post.refresh_from_db()
    original_updated_at = post.updated_at
    old_detail_etag = client.get(post.get_absolute_url())["ETag"]
    old_media_etag = client.get(stable_url)["ETag"]
    cache.set(f"post:{post.pk}:body_html", post.content_html, timeout=3600)

    dry_run_output = StringIO()
    call_command(
        "rebuild_content_html", "--slug", post.slug, "--dry-run", stdout=dry_run_output
    )
    post.refresh_from_db()
    assert "candidates=1 changed=1 skipped=0 errors=0 dry_run=True" in dry_run_output.getvalue()
    assert stale_url in post.content_html

    output = StringIO()
    call_command("rebuild_content_html", "--slug", post.slug, stdout=output)
    post.refresh_from_db()
    assert "candidates=1 changed=1 skipped=0 errors=0 dry_run=False" in output.getvalue()
    assert post.content == source_markdown
    assert stable_url in post.content_html
    assert "X-Amz-" not in post.content_html
    assert post.updated_at > original_updated_at
    assert stable_url in post.body_content_html

    detail = client.get(post.get_absolute_url(), HTTP_IF_NONE_MATCH=old_detail_etag)
    media_response = client.get(stable_url, HTTP_IF_NONE_MATCH=old_media_etag)
    assert detail.status_code == 200
    assert media_response.status_code == 200
    assert client.get(post.get_absolute_url(), HTTP_IF_NONE_MATCH=detail["ETag"]).status_code == 304
    assert client.get(stable_url, HTTP_IF_NONE_MATCH=media_response["ETag"]).status_code == 304

    second_output = StringIO()
    call_command("rebuild_content_html", "--slug", post.slug, stdout=second_output)
    assert "candidates=1 changed=0 skipped=1 errors=0 dry_run=False" in second_output.getvalue()


@pytest.mark.django_db
def test_rebuild_content_html_slug_requires_an_existing_post():
    """A typo cannot silently turn a targeted repair into a no-op."""
    with pytest.raises(CommandError, match="No post found for slug"):
        call_command("rebuild_content_html", "--slug", "missing-post")
