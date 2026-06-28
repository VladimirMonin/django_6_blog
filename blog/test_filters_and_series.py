import json

import pytest
from django.test import Client

from api.models import ApiKey
from blog.models import Post, Series
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
