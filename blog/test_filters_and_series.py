import json
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup
from django.test import Client

from api.models import ApiKey
from blog.models import Category, Post, Series, Tag
from publisher.client import publish_post
from publisher.parser import parse_markdown_file


@pytest.mark.django_db
def test_post_list_filters_by_content_type_query_param():
    Post.objects.create(
        title="Article A",
        description="A",
        content="body",
        slug="article-a",
        content_type=Post.ContentType.ARTICLE,
        status=Post.Status.PUBLISHED,
    )
    Post.objects.create(
        title="Video B",
        description="B",
        content="body",
        slug="video-b",
        content_type=Post.ContentType.VIDEO,
        media_url="https://example.com/video.mp4",
        status=Post.Status.PUBLISHED,
    )

    client = Client()
    response = client.get("/?type=video")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Video B" in body
    assert "Article A" not in body


@pytest.mark.django_db
def test_post_list_keeps_content_type_in_search_form():
    Post.objects.create(
        title="Podcast One",
        description="Podcast desc",
        content="body",
        slug="podcast-one",
        content_type=Post.ContentType.PODCAST,
        media_url="https://example.com/podcast.opus",
        status=Post.Status.PUBLISHED,
    )

    client = Client()
    response = client.get("/?type=podcast")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'name="type" value="podcast"' in body


def _query_params(url):
    return parse_qs(urlparse(url).query)


def _assert_active_filters(url, *, search, category, tag, content_type):
    params = _query_params(url)
    assert params["search"] == [search]
    assert params["category"] == [category]
    assert params["tag"] == [tag]
    assert params["type"] == [content_type]
    return params


@pytest.mark.django_db
def test_post_list_preserves_all_filters_across_navigation_links():
    active_category = Category.objects.create(name="Видео", slug="video-category")
    other_category = Category.objects.create(name="Другое", slug="other-category")
    active_tag = Tag.objects.create(name="HTMX", slug="htmx")
    other_tag = Tag.objects.create(name="Django", slug="django")
    for index in range(7):
        post = Post.objects.create(
            title=f"Навигация video {index}",
            description="Фильтры",
            content="body",
            slug=f"navigation-video-{index}",
            category=active_category,
            content_type=Post.ContentType.VIDEO,
            media_url="https://example.com/video.mp4",
            status=Post.Status.PUBLISHED,
        )
        post.tags.add(active_tag)
    other_post = Post.objects.create(
        title="Навигация video other",
        description="Фильтры",
        content="body",
        slug="navigation-video-other",
        category=other_category,
        content_type=Post.ContentType.VIDEO,
        media_url="https://example.com/other.mp4",
        status=Post.Status.PUBLISHED,
    )
    other_post.tags.add(other_tag)

    response = Client().get(
        "/",
        {
            "search": "Навигация",
            "category": active_category.slug,
            "tag": active_tag.slug,
            "type": Post.ContentType.VIDEO,
        },
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.content, "html.parser")
    paginator = page.select_one("#paginator-nav")
    assert paginator is not None
    for link in paginator.select("a.page-link"):
        params = _assert_active_filters(
            link["href"],
            search="Навигация",
            category=active_category.slug,
            tag=active_tag.slug,
            content_type=Post.ContentType.VIDEO,
        )
        assert "load_more" not in params
        assert _query_params(link["hx-get"]) == params

    load_more = paginator.select_one("button[hx-get]")
    load_more_params = _assert_active_filters(
        load_more["hx-get"],
        search="Навигация",
        category=active_category.slug,
        tag=active_tag.slug,
        content_type=Post.ContentType.VIDEO,
    )
    assert load_more_params["page"] == ["2"]
    assert load_more_params["load_more"] == ["true"]

    htmx_page_two = Client().get(
        "/",
        {
            "search": "Навигация",
            "category": active_category.slug,
            "tag": active_tag.slug,
            "type": Post.ContentType.VIDEO,
            "page": "2",
        },
        HTTP_HX_REQUEST="true",
    )
    assert htmx_page_two.status_code == 200
    htmx_paginator = BeautifulSoup(htmx_page_two.content, "html.parser").select_one(
        "#paginator-nav[hx-swap-oob='true']"
    )
    previous_link = htmx_paginator.select_one("a.page-link")
    previous_params = _assert_active_filters(
        previous_link["href"],
        search="Навигация",
        category=active_category.slug,
        tag=active_tag.slug,
        content_type=Post.ContentType.VIDEO,
    )
    assert previous_params["page"] == ["1"]
    assert "load_more" not in previous_params
    assert _query_params(previous_link["hx-get"]) == previous_params

    category_link = page.select_one(f'a[href*="category={other_category.slug}"]')
    category_params = _assert_active_filters(
        category_link["href"],
        search="Навигация",
        category=other_category.slug,
        tag=active_tag.slug,
        content_type=Post.ContentType.VIDEO,
    )
    assert "page" not in category_params
    assert "load_more" not in category_params
    assert _query_params(category_link["hx-get"]) == category_params

    tag_link = page.select_one(f'a[href*="tag={other_tag.slug}"]')
    tag_params = _assert_active_filters(
        tag_link["href"],
        search="Навигация",
        category=active_category.slug,
        tag=other_tag.slug,
        content_type=Post.ContentType.VIDEO,
    )
    assert "page" not in tag_params
    assert "load_more" not in tag_params
    assert _query_params(tag_link["hx-get"]) == tag_params


@pytest.mark.django_db
def test_series_navigation_prev_next_on_detail():
    series = Series.objects.create(name="Django Course")
    first = Post.objects.create(
        title="Lesson 1",
        description="d1",
        content="body",
        slug="lesson-1",
        series=series,
        series_order=1,
        status=Post.Status.PUBLISHED,
    )
    second = Post.objects.create(
        title="Lesson 2",
        description="d2",
        content="body",
        slug="lesson-2",
        series=series,
        series_order=2,
        status=Post.Status.PUBLISHED,
    )
    third = Post.objects.create(
        title="Lesson 3",
        description="d3",
        content="body",
        slug="lesson-3",
        series=series,
        series_order=3,
        status=Post.Status.PUBLISHED,
    )

    client = Client()
    response = client.get(f"/post/{second.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Серия: Django Course" in body
    assert first.slug in body
    assert third.slug in body
    assert "2 / 3" in body


@pytest.mark.django_db
def test_series_navigation_absent_without_series():
    post = Post.objects.create(
        title="Standalone",
        description="standalone",
        content="body",
        slug="standalone",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    assert "Навигация по серии" not in response.content.decode()


@pytest.mark.django_db
def test_cli_e2e_publish_series_posts_and_navigation(tmp_path, live_server):
    key = ApiKey.objects.create(name="Series Agent")

    notes = [
        (
            "lesson-1.md",
            "---\n"
            "title: Python Lesson 1\n"
            "description: intro\n"
            "series: Python Basics\n"
            "series_order: 1\n"
            "---\n"
            "Lesson 1 body.\n",
        ),
        (
            "lesson-2.md",
            "---\n"
            "title: Python Lesson 2\n"
            "description: second\n"
            "series: Python Basics\n"
            "series_order: 2\n"
            "---\n"
            "Lesson 2 body.\n",
        ),
        (
            "lesson-3.md",
            "---\n"
            "title: Python Lesson 3\n"
            "description: third\n"
            "series: Python Basics\n"
            "series_order: 3\n"
            "---\n"
            "Lesson 3 body.\n",
        ),
    ]

    slugs = []
    for filename, text in notes:
        note = tmp_path / filename
        note.write_text(text, encoding="utf-8")
        payload = parse_markdown_file(note)
        result = publish_post(url=live_server.url, api_key=key.token, payload=payload)
        slugs.append(result["slug"])
        assert result["series"] == "Python Basics"

    client = Client()
    response = client.get(f"/post/{slugs[1]}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert slugs[0] in body
    assert slugs[2] in body
    assert "2 / 3" in body

    posts = list(Series.objects.get(name="Python Basics").posts.order_by("series_order"))
    assert [post.title for post in posts] == ["Python Lesson 1", "Python Lesson 2", "Python Lesson 3"]
