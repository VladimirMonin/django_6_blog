"""Tests for API operational features: bulk publish, sort, stats, rate limiting, validation."""

import json

import pytest
from django.test import Client

from api.decorators import _reset_rate_limit
from api.models import ApiKey
from blog.models import Category, Post


@pytest.fixture
def api_client():
    _reset_rate_limit()
    key = ApiKey.objects.create(name="Operational Agent")
    client = Client()
    return client, key


# ─── Bulk Publish ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_bulk_publish_creates_3_posts_in_one_call(api_client):
    """POST /api/v1/posts/bulk/ with 3 posts creates all 3."""
    client, key = api_client
    payload = {
        "posts": [
            {
                "title": "Bulk Post One",
                "description": "First bulk post",
                "content": "Content one",
            },
            {
                "title": "Bulk Post Two",
                "description": "Second bulk post",
                "content": "Content two",
            },
            {
                "title": "Bulk Post Three",
                "description": "Third bulk post",
                "content": "Content three",
            },
        ]
    }
    response = client.post(
        "/api/v1/posts/bulk/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    assert body["created"] == 3
    assert len(body["results"]) == 3
    for result in body["results"]:
        assert result["success"] is True
        assert result["slug"]
    # Verify posts exist in DB
    assert Post.objects.filter(title__startswith="Bulk Post").count() == 3


@pytest.mark.django_db
def test_bulk_publish_validates_each_post(api_client):
    """Bulk publish reports errors for invalid posts but creates valid ones."""
    client, key = api_client
    payload = {
        "posts": [
            {
                "title": "Valid Bulk Post",
                "description": "Valid",
                "content": "Valid content",
            },
            {
                "title": "Invalid Post",
                # missing description and content
            },
        ]
    }
    response = client.post(
        "/api/v1/posts/bulk/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201  # at least one created
    body = json.loads(response.content)
    assert body["created"] == 1
    assert body["results"][0]["success"] is True
    assert body["results"][1]["success"] is False


# ─── Sort ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_sort_by_title_ascending(api_client):
    """?sort=title returns posts sorted A-Z."""
    client, key = api_client
    for title in ["Charlie", "Alpha", "Bravo"]:
        Post.objects.create(
            title=title,
            description="desc",
            content="content",
            slug=title.lower(),
            status=Post.Status.PUBLISHED,
        )
    response = client.get(
        "/api/v1/posts/?sort=title",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    titles = [item["title"] for item in data["results"]]
    assert titles == ["Alpha", "Bravo", "Charlie"]


@pytest.mark.django_db
def test_sort_by_title_descending(api_client):
    """?sort=-title returns posts sorted Z-A."""
    client, key = api_client
    for title in ["Charlie", "Alpha", "Bravo"]:
        Post.objects.create(
            title=title,
            description="desc",
            content="content",
            slug=title.lower(),
            status=Post.Status.PUBLISHED,
        )
    response = client.get(
        "/api/v1/posts/?sort=-title",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    titles = [item["title"] for item in data["results"]]
    assert titles == ["Charlie", "Bravo", "Alpha"]


@pytest.mark.django_db
def test_sort_by_invalid_field_returns_400(api_client):
    """Invalid sort field returns 400."""
    client, key = api_client
    response = client.get(
        "/api/v1/posts/?sort=invalid_field",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 400
    body = json.loads(response.content)
    assert "error" in body
    assert "invalid_field" in body["error"].lower() or "invalid" in body["error"].lower()


@pytest.mark.django_db
def test_sort_default_is_created_at_desc(api_client):
    """Default sort (no sort param) is -created_at."""
    client, key = api_client
    p1 = Post.objects.create(
        title="First Created",
        description="desc",
        content="content",
        slug="first-created",
        status=Post.Status.PUBLISHED,
    )
    p2 = Post.objects.create(
        title="Second Created",
        description="desc",
        content="content",
        slug="second-created",
        status=Post.Status.PUBLISHED,
    )
    response = client.get(
        "/api/v1/posts/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    # Second created should come first (newest first)
    assert data["results"][0]["title"] == "Second Created"
    assert data["results"][1]["title"] == "First Created"


@pytest.mark.django_db
def test_sort_by_view_count(api_client):
    """?sort=-view_count sorts by views descending."""
    client, key = api_client
    Post.objects.create(
        title="Low Views",
        description="desc",
        content="content",
        slug="low-views",
        view_count=5,
        status=Post.Status.PUBLISHED,
    )
    Post.objects.create(
        title="High Views",
        description="desc",
        content="content",
        slug="high-views",
        view_count=100,
        status=Post.Status.PUBLISHED,
    )
    response = client.get(
        "/api/v1/posts/?sort=-view_count",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["results"][0]["title"] == "High Views"
    assert data["results"][1]["title"] == "Low Views"


# ─── Stats ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_stats_returns_correct_counts(api_client):
    """GET /api/v1/stats/ returns correct counts for status, content_type, category, views, likes, featured."""
    client, key = api_client
    cat1 = Category.objects.create(name="Tech", slug="tech")
    cat2 = Category.objects.create(name="News", slug="news")

    # Published articles
    Post.objects.create(
        title="P1", description="d", content="c", slug="p1",
        status=Post.Status.PUBLISHED, content_type=Post.ContentType.ARTICLE,
        category=cat1, view_count=10, like_count=2, is_featured=True,
    )
    Post.objects.create(
        title="P2", description="d", content="c", slug="p2",
        status=Post.Status.PUBLISHED, content_type=Post.ContentType.ARTICLE,
        category=cat1, view_count=20, like_count=3,
    )
    # Draft video
    Post.objects.create(
        title="P3", description="d", content="c", slug="p3",
        status=Post.Status.DRAFT, content_type=Post.ContentType.VIDEO,
        category=cat2, media_url="https://example.com/v.mp4", view_count=5,
    )
    # Published podcast
    Post.objects.create(
        title="P4", description="d", content="c", slug="p4",
        status=Post.Status.PUBLISHED, content_type=Post.ContentType.PODCAST,
        category=cat2, media_url="https://example.com/p.opus",
        view_count=15, like_count=1, is_featured=True,
    )

    response = client.get(
        "/api/v1/stats/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)

    # By status
    assert data["by_status"]["published"] == 3
    assert data["by_status"]["draft"] == 1
    assert data["by_status"]["archived"] == 0

    # By content type
    assert data["by_content_type"]["article"] == 2
    assert data["by_content_type"]["video"] == 1
    assert data["by_content_type"]["podcast"] == 1
    assert data["by_content_type"]["audio"] == 0

    # By category (top 5)
    assert data["by_category"]["Tech"] == 2
    assert data["by_category"]["News"] == 2

    # Total views: 10 + 20 + 5 + 15 = 50
    assert data["total_views"] == 50

    # Total likes: 2 + 3 + 1 = 6
    assert data["total_likes"] == 6

    # Featured count: 2
    assert data["featured_count"] == 2


@pytest.mark.django_db
def test_stats_requires_stats_permission():
    """API key without 'stats' permission gets 403."""
    from api.decorators import _reset_rate_limit
    _reset_rate_limit()
    key = ApiKey.objects.create(name="No Stats Agent", permissions=["read"])
    client = Client()
    response = client.get(
        "/api/v1/stats/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 403


# ─── Rate Limiting ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_rate_limit_returns_429_after_60_requests(api_client):
    """After 60 requests in quick succession, 61st returns 429."""
    client, key = api_client
    # Make 60 requests (should all succeed)
    for i in range(60):
        response = client.get(
            "/api/v1/posts/",
            HTTP_AUTHORIZATION="Bearer " + key.token,
        )
        assert response.status_code == 200, f"Request {i+1} failed with {response.status_code}"

    # 61st request should be rate-limited
    response = client.get(
        "/api/v1/posts/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 429
    body = json.loads(response.content)
    assert body["error"] == "Rate limit exceeded"
    assert "retry_after" in body
    assert isinstance(body["retry_after"], int)
    assert body["retry_after"] > 0


# ─── Better Validation ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_video_without_media_url_returns_400(api_client):
    """Publishing a video post without media_url returns 400."""
    client, key = api_client
    payload = {
        "title": "Video Without URL",
        "description": "Missing media_url",
        "content": "Video content",
        "content_type": "video",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 400
    body = json.loads(response.content)
    assert "errors" in body
    assert any("media_url" in err for err in body["errors"])


@pytest.mark.django_db
def test_audio_without_media_url_returns_400(api_client):
    """Publishing an audio post without media_url returns 400."""
    client, key = api_client
    payload = {
        "title": "Audio Without URL",
        "description": "Missing media_url",
        "content": "Audio content",
        "content_type": "audio",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 400
    body = json.loads(response.content)
    assert any("media_url" in err for err in body["errors"])


@pytest.mark.django_db
def test_podcast_without_media_url_returns_400(api_client):
    """Publishing a podcast post without media_url returns 400."""
    client, key = api_client
    payload = {
        "title": "Podcast Without URL",
        "description": "Missing media_url",
        "content": "Podcast content",
        "content_type": "podcast",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 400
    body = json.loads(response.content)
    assert any("media_url" in err for err in body["errors"])


@pytest.mark.django_db
def test_video_with_media_url_succeeds(api_client):
    """Publishing a video post with media_url succeeds."""
    client, key = api_client
    payload = {
        "title": "Video With URL",
        "description": "Has media_url",
        "content": "Video content",
        "content_type": "video",
        "media_url": "https://example.com/video.mp4",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_article_without_media_url_succeeds(api_client):
    """Articles don't require media_url."""
    client, key = api_client
    payload = {
        "title": "Plain Article",
        "description": "No media needed",
        "content": "Article content",
        "content_type": "article",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_invalid_timecode_format_returns_400(api_client):
    """Timecodes with invalid format (bad seconds) are rejected."""
    client, key = api_client
    payload = {
        "title": "Bad Timecodes",
        "description": "Invalid time format",
        "content": "Content",
        "content_type": "video",
        "media_url": "https://example.com/v.mp4",
        "timecodes": [
            {"time": "0:99", "label": "Invalid seconds"},
        ],
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 400
    body = json.loads(response.content)
    assert any("timecode" in err.lower() for err in body["errors"])


@pytest.mark.django_db
def test_valid_timecodes_succeed(api_client):
    """Timecodes with valid M:SS and H:MM:SS formats are accepted."""
    client, key = api_client
    payload = {
        "title": "Good Timecodes",
        "description": "Valid time format",
        "content": "Content",
        "content_type": "podcast",
        "media_url": "https://example.com/p.opus",
        "timecodes": [
            {"time": "0:00", "label": "Intro"},
            {"time": "1:30", "label": "Main topic"},
            {"time": "1:02:03", "label": "Q&A"},
        ],
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201