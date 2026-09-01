"""Regression tests for public llms.txt and Markdown discovery surfaces."""

import re

import pytest
from django.test import override_settings
from django.utils import timezone

from blog.models import Post


def create_post(title, slug, *, description="Public description", content="Public body"):
    """Create a published post with explicit public discovery fields."""

    return Post.objects.create(
        title=title,
        description=description,
        content=content,
        slug=slug,
        status=Post.Status.PUBLISHED,
    )


@pytest.mark.django_db
def test_llms_txt_is_compact_public_and_consistent_with_sitemap(client):
    """The v2 pointer contains only public pages and recent public post metadata."""

    public_post = create_post(
        "Публичная статья",
        "public-discovery",
        description="Короткое публичное описание",
        content="Тело статьи не должно дублироваться в llms.txt.",
    )
    draft = Post.objects.create(
        title="Черновик",
        description="Скрытое описание",
        content="Скрытое тело",
        slug="draft-discovery",
        status=Post.Status.DRAFT,
    )
    archived = Post.objects.create(
        title="Архив",
        description="Скрытое описание",
        content="Скрытое тело",
        slug="archived-discovery",
        status=Post.Status.ARCHIVED,
    )
    deleted = create_post(
        "Soft-deleted",
        "deleted-discovery",
        description="Скрытое описание",
        content="Скрытое тело",
    )
    deleted.deleted_at = timezone.now()
    deleted.save(update_fields=["deleted_at", "updated_at"])

    with override_settings(ALLOWED_HOSTS=["blog.example"]):
        response = client.get(
            "/llms.txt?source=share",
            secure=True,
            HTTP_HOST="blog.example",
        )
        sitemap = client.get("/sitemap.xml", secure=True, HTTP_HOST="blog.example")
        cached = client.get(
            "/llms.txt",
            secure=True,
            HTTP_HOST="blog.example",
            HTTP_IF_NONE_MATCH=response.headers["ETag"],
        )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.charset == "utf-8"
    body = response.content.decode("utf-8")
    assert body.startswith("# Django 6 Blog\n")
    assert "This experiment does not guarantee indexing, citation, traffic, or model training." in body
    assert "https://blog.example/" in body
    assert "https://blog.example/about/" in body
    assert "https://blog.example/sitemap.xml" in body
    assert f"https://blog.example{public_post.get_absolute_url()}" in body
    assert f"https://blog.example/post/{public_post.slug}.md" in body
    assert "source=share" not in body
    assert public_post.description in body
    assert public_post.content not in body
    for hidden_post in (draft, archived, deleted):
        assert hidden_post.title not in body
        assert hidden_post.description not in body
        assert hidden_post.content not in body
    assert "/admin/" not in body
    assert "/api/" not in body
    assert public_post.get_absolute_url() in sitemap.content.decode("utf-8")
    assert response.headers["ETag"]
    assert response.headers["Last-Modified"]
    assert cached.status_code == 304


@pytest.mark.django_db
def test_llms_full_is_not_created(client):
    """No full-site duplicate endpoint is exposed by the discovery experiment."""

    assert client.get("/llms-full.txt").status_code == 404


@pytest.mark.django_db
@override_settings(SITE_AUTHOR="Автор \"Тест\" \\ Юникод")
def test_post_markdown_uses_public_source_and_canonical_html_link(client):
    """Markdown has safe public metadata and the exact stored Markdown body."""

    content = "## Раздел\n\nТело с Unicode: ёлка, 漢字 и \\ обратный слеш."
    post = create_post(
        'Заголовок "тест"',
        "markdown-discovery",
        description="Описание для Markdown",
        content=content,
    )

    with override_settings(ALLOWED_HOSTS=["blog.example"]):
        response = client.get(
            f"/post/{post.slug}.md?from=llms",
            secure=True,
            HTTP_HOST="blog.example",
        )
        detail = client.get(
            f"{post.get_absolute_url()}?from=llms",
            secure=True,
            HTTP_HOST="blog.example",
        )
        cached = client.get(
            f"/post/{post.slug}.md",
            secure=True,
            HTTP_HOST="blog.example",
            HTTP_IF_NONE_MATCH=response.headers["ETag"],
        )

    canonical = f"https://blog.example{post.get_absolute_url()}"
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/markdown; charset=utf-8"
    assert response.charset == "utf-8"
    assert response.headers["Link"] == f'<{canonical}>; rel="canonical"'
    assert "\r" not in response.headers["Link"]
    assert "\n" not in response.headers["Link"]
    assert response.headers["ETag"]
    assert response.headers["Last-Modified"]
    body = response.content.decode("utf-8")
    assert '# Заголовок "тест"' in body
    assert "> Описание для Markdown" in body
    assert '- Author: Автор "Тест" \\\\ Юникод' in body
    assert "- Published: " in body
    assert "- Modified: " in body
    assert f"- Canonical: <{canonical}>" in body
    assert body.endswith(f"{content}\n")
    assert post.source_id is None
    assert "content_html" not in body
    assert "from=llms" not in body
    assert detail.status_code == 200
    detail_body = detail.content.decode("utf-8")
    assert re.search(
        rf'<link rel="alternate" type="text/markdown" href="/post/{post.slug}\.md">',
        detail_body,
    )
    assert '<link rel="describedby" href="/llms.txt">' in detail_body
    assert cached.status_code == 304


@pytest.mark.django_db
def test_markdown_link_header_cannot_be_derived_from_post_text(client):
    """Untrusted title and description do not control the canonical Link header."""

    post = create_post(
        "Безопасный заголовок",
        "header-safe-markdown",
        description="Описание\r\n<https://attacker.example>; rel=canonical",
    )

    with override_settings(ALLOWED_HOSTS=["blog.example"]):
        response = client.get(
            f"/post/{post.slug}.md",
            secure=True,
            HTTP_HOST="blog.example",
        )

    assert response.status_code == 200
    assert response.headers["Link"] == (
        "<https://blog.example/post/header-safe-markdown/>; rel=\"canonical\""
    )
    assert "attacker.example" not in response.headers["Link"]
    assert "\r" not in response.headers["Link"]
    assert "\n" not in response.headers["Link"]


@pytest.mark.django_db
@pytest.mark.parametrize("status", [Post.Status.DRAFT, Post.Status.ARCHIVED])
def test_non_public_post_markdown_returns_404(client, status):
    """Draft and archived post Markdown is unavailable just like public detail HTML."""

    post = Post.objects.create(
        title=f"Hidden {status}",
        description="Not public",
        content="Hidden body",
        slug=f"hidden-markdown-{status}",
        status=status,
    )

    assert client.get(f"/post/{post.slug}.md").status_code == 404


@pytest.mark.django_db
def test_soft_deleted_post_markdown_returns_404(client):
    """A soft-deleted published post never has a public Markdown surface."""

    post = create_post("Deleted", "deleted-markdown")
    post.deleted_at = timezone.now()
    post.save(update_fields=["deleted_at", "updated_at"])

    assert client.get(f"/post/{post.slug}.md").status_code == 404
