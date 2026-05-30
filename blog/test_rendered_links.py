from urllib.parse import urljoin, urlparse

import pytest
from bs4 import BeautifulSoup

from blog.models import Category, Post, Tag


SKIPPED_SCHEMES = {"mailto", "tel", "javascript"}


def create_post(title, content="Smoke test content", *, category=None, tags=()):
    post = Post.objects.create(
        title=title,
        content=content,
        status=Post.Status.PUBLISHED,
        category=category,
    )
    if tags:
        post.tags.set(tags)
    return post


@pytest.fixture
def linked_posts():
    category = Category.objects.create(name="Smoke Django", slug="smoke-django")
    tag = Tag.objects.create(name="Rendered Links", slug="rendered-links")
    posts = []
    for index in range(7):
        posts.append(
            create_post(
                f"Rendered link smoke {index}",
                content=(
                    "Rendered smoke body with an [about link](/about/) and "
                    "an [external link](https://example.com/ignored)."
                ),
                category=category,
                tags=[tag],
            )
        )
    return {"category": category, "tag": tag, "posts": posts}


def same_site_anchor_hrefs(html, source_path):
    page = BeautifulSoup(html, "html.parser")
    hrefs = []
    for anchor in page.select("a[href]"):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        parsed = urlparse(href)
        if parsed.scheme in SKIPPED_SCHEMES or parsed.netloc:
            continue
        resolved = urljoin(source_path, href)
        if resolved.startswith("/admin/"):
            continue
        hrefs.append(resolved)
    return hrefs


@pytest.mark.django_db
def test_rendered_index_links_return_success(client, linked_posts):
    response = client.get("/")

    assert response.status_code == 200
    page = BeautifulSoup(response.content, "html.parser")
    assert page.select_one("a.post-card-title-link") is not None
    assert page.select_one("a.post-badge-category[href*='category=smoke-django']") is not None
    assert page.select_one("a.post-badge-tag[href*='tag=rendered-links']") is not None
    assert page.select_one("a.page-link[href*='page=2']") is not None

    broken = []
    for href in same_site_anchor_hrefs(response.content, "/"):
        linked_response = client.get(href)
        if linked_response.status_code >= 400:
            broken.append((href, linked_response.status_code))

    assert broken == []


@pytest.mark.django_db
def test_rendered_about_links_return_success(client, linked_posts):
    response = client.get("/about/")

    assert response.status_code == 200
    assert same_site_anchor_hrefs(response.content, "/about/")

    broken = []
    for href in same_site_anchor_hrefs(response.content, "/about/"):
        linked_response = client.get(href)
        if linked_response.status_code >= 400:
            broken.append((href, linked_response.status_code))

    assert broken == []


@pytest.mark.django_db
def test_rendered_detail_links_return_success(client, linked_posts):
    post = linked_posts["posts"][0]
    source_path = post.get_absolute_url()
    response = client.get(source_path)

    assert response.status_code == 200
    page = BeautifulSoup(response.content, "html.parser")
    assert page.select_one("a[href='/?category=smoke-django']") is not None
    assert page.select_one("a[href='/?tag=rendered-links']") is not None

    broken = []
    for href in same_site_anchor_hrefs(response.content, source_path):
        linked_response = client.get(href)
        if linked_response.status_code >= 400:
            broken.append((href, linked_response.status_code))

    assert broken == []


@pytest.mark.django_db
def test_rendered_filtered_paginated_index_links_preserve_query_and_return_success(client, linked_posts):
    source_path = "/?search=Rendered&category=smoke-django&tag=rendered-links&page=2"
    response = client.get(source_path)

    assert response.status_code == 200
    page = BeautifulSoup(response.content, "html.parser")
    previous_link = page.select_one("a.page-link[href*='page=1']")
    assert previous_link is not None
    assert "search=Rendered" in previous_link["href"]
    assert "category=smoke-django" in previous_link["href"]
    assert "tag=rendered-links" in previous_link["href"]

    broken = []
    for href in same_site_anchor_hrefs(response.content, source_path):
        linked_response = client.get(href)
        if linked_response.status_code >= 400:
            broken.append((href, linked_response.status_code))

    assert broken == []
