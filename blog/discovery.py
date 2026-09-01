"""Public llms.txt and Markdown representations for published posts only."""

import hashlib

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import condition

from .models import Post
from .seo import site_entities


LLMS_VERSION = "v2"
LLMS_POST_LIMIT = 20


def _public_posts():
    """Return the canonical queryset shared by public discovery endpoints."""

    return Post.objects.filter(
        status=Post.Status.PUBLISHED,
        deleted_at__isnull=True,
    )


def _markdown_inline(value: str) -> str:
    """Keep discovery metadata on one Markdown line without adding links."""

    normalized = " ".join(value.split())
    return normalized.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _post_html_url(request: HttpRequest, post: Post) -> str:
    """Return a query-free absolute URL for the canonical HTML post detail."""

    return request.build_absolute_uri(post.get_absolute_url())


def _post_markdown_url(request: HttpRequest, post: Post) -> str:
    """Return the query-free absolute Markdown representation URL for a post."""

    return request.build_absolute_uri(
        reverse("post_markdown", kwargs={"slug": post.slug})
    )


def _llms_last_modified(request: HttpRequest):
    """Return the latest public-post modification time for llms.txt caching."""

    return (
        _public_posts()
        .order_by("-updated_at")
        .values_list("updated_at", flat=True)
        .first()
    )


def _llms_etag(request: HttpRequest) -> str:
    """Hash every value rendered into the dynamic, host-specific llms.txt."""

    public_post_state = tuple(
        _public_posts()
        .order_by("-updated_at", "slug")
        .values_list("pk", "slug", "title", "description", "updated_at")[:LLMS_POST_LIMIT]
    )
    source = repr(
        (
            LLMS_VERSION,
            request.build_absolute_uri(reverse("post_list")),
            site_entities(request)["person"]["name"],
            public_post_state,
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _post_markdown_state(request: HttpRequest, slug: str):
    """Return the public row state that determines a Markdown representation."""

    return (
        _public_posts()
        .filter(slug=slug)
        .values_list(
            "pk",
            "title",
            "description",
            "content",
            "created_at",
            "published_at",
            "updated_at",
        )
        .first()
    )


def _post_markdown_last_modified(request: HttpRequest, *args, **kwargs):
    """Return the public post modification time for conditional Markdown GETs."""

    slug = kwargs.get("slug")
    if not slug:
        return None
    state = _post_markdown_state(request, slug)
    return state[-1] if state else None


def _post_markdown_etag(request: HttpRequest, *args, **kwargs):
    """Hash the Markdown response inputs without placing user text in headers."""

    slug = kwargs.get("slug")
    if not slug:
        return None
    state = _post_markdown_state(request, slug)
    if not state:
        return None
    source = repr(
        (
            LLMS_VERSION,
            request.build_absolute_uri(
                reverse("post_detail", kwargs={"slug": slug})
            ),
            site_entities(request)["person"]["name"],
            state,
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


@condition(last_modified_func=_llms_last_modified, etag_func=_llms_etag)
def llms_txt(request: HttpRequest) -> HttpResponse:
    """Return a compact v2 discovery pointer without duplicating post bodies."""

    site = site_entities(request)
    public_posts = _public_posts().order_by("-updated_at", "slug")[:LLMS_POST_LIMIT]
    lines = [
        "# Django 6 Blog",
        "",
        "> Compact v2 discovery pointer for public pages and recent published posts.",
        "> This experiment does not guarantee indexing, citation, traffic, or model training.",
        "",
        "## Public pages",
        f"- [Home]({site['website']['url']})",
        f"- [About]({site['person']['url']})",
        f"- [Sitemap]({request.build_absolute_uri(reverse('sitemap'))})",
        f"- [RSS]({request.build_absolute_uri(reverse('feed_rss'))})",
        f"- [Atom]({request.build_absolute_uri(reverse('feed_atom'))})",
        "",
        "## Recent published posts",
    ]
    for post in public_posts:
        lines.append(
            f"- [{_markdown_inline(post.title)}]({_post_html_url(request, post)}): "
            f"{_markdown_inline(post.description)} "
            f"([Markdown]({_post_markdown_url(request, post)}))"
        )
    lines.append("")
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


@condition(
    last_modified_func=_post_markdown_last_modified,
    etag_func=_post_markdown_etag,
)
def post_markdown(request: HttpRequest, slug: str) -> HttpResponse:
    """Return one published post from its stored public Markdown source."""

    post = get_object_or_404(_public_posts(), slug=slug)
    canonical = _post_html_url(request, post)
    site = site_entities(request)
    published_at = post.published_at or post.created_at
    document = "\n".join(
        [
            f"# {_markdown_inline(post.title)}",
            "",
            f"> {_markdown_inline(post.description)}",
            "",
            "## Publication",
            f"- Author: {_markdown_inline(site['person']['name'])}",
            f"- Published: {published_at.isoformat()}",
            f"- Modified: {post.updated_at.isoformat()}",
            f"- Canonical: <{canonical}>",
            "",
            "---",
            "",
            post.content,
            "",
        ]
    )
    response = HttpResponse(document, content_type="text/markdown; charset=utf-8")
    response["Link"] = f'<{canonical}>; rel="canonical"'
    return response
