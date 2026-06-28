import json
import pytest
from api.models import ApiKey
from api.decorators import require_api_key
from django.http import JsonResponse
from django.test import Client


@pytest.mark.django_db
def test_api_key_creation_generates_token():
    key = ApiKey.objects.create(name="Hermes agent")
    assert key.token
    assert len(key.token) >= 32
    assert key.is_active is True
    assert key.created_at is not None


@pytest.mark.django_db
def test_api_key_str_shows_name_and_masked_token():
    key = ApiKey.objects.create(name="Blog poster")
    assert "Blog poster" in str(key)
    assert key.token[:8] in str(key)
    assert key.token[-4:] not in str(key)


@pytest.mark.django_db
def test_api_key_revocation():
    key = ApiKey.objects.create(name="Temp agent")
    assert key.is_active
    key.revoke()
    assert not key.is_active


@pytest.mark.django_db
def test_api_key_verify_returns_true_for_valid_key():
    key = ApiKey.objects.create(name="Agent")
    assert ApiKey.verify(key.token) is not None
    assert ApiKey.verify(key.token).pk == key.pk


@pytest.mark.django_db
def test_api_key_verify_returns_none_for_invalid_key():
    ApiKey.objects.create(name="Agent")
    assert ApiKey.verify("invalid-token-string") is None


@pytest.mark.django_db
def test_api_key_verify_returns_none_for_revoked_key():
    key = ApiKey.objects.create(name="Agent")
    key.revoke()
    assert ApiKey.verify(key.token) is None


@pytest.mark.django_db
def test_require_api_key_returns_401_without_header():
    client = Client()

    @require_api_key
    def view(request):
        return JsonResponse({"ok": True})

    response = view(client.get("/").wsgi_request)
    assert response.status_code == 401
    body = json.loads(response.content)
    assert "error" in body


@pytest.mark.django_db
def test_require_api_key_returns_401_with_invalid_token():
    client = Client()

    @require_api_key
    def view(request):
        return JsonResponse({"ok": True})

    request = client.get("/", HTTP_AUTHORIZATION="Bearer wrong-token").wsgi_request
    response = view(request)
    assert response.status_code == 401


@pytest.mark.django_db
def test_require_api_key_passes_with_valid_token():
    key = ApiKey.objects.create(name="Agent")
    client = Client()

    @require_api_key
    def view(request):
        return JsonResponse({"ok": True, "key": request.api_key.name})

    request = client.get("/", HTTP_AUTHORIZATION=f"Bearer {key.token}").wsgi_request
    response = view(request)
    assert response.status_code == 200
    body = json.loads(response.content)
    assert body["ok"] is True
    assert body["key"] == "Agent"


@pytest.mark.django_db
def test_require_api_key_rejects_revoked_key():
    key = ApiKey.objects.create(name="Agent")
    key.revoke()
    client = Client()

    @require_api_key
    def view(request):
        return JsonResponse({"ok": True})

    request = client.get("/", HTTP_AUTHORIZATION=f"Bearer {key.token}").wsgi_request
    response = view(request)
    assert response.status_code == 401


@pytest.mark.django_db
def test_publish_post_creates_published_post():
    key = ApiKey.objects.create(name="Agent")
    client = Client()
    payload = {
        "title": "Test API Post",
        "description": "Created via API",
        "content": "# Hello\n\nThis is a **test** post.",
        "content_type": "article",
        "tags": ["Python", "Django"],
        "category": "Testing",
        "status": "published",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    assert body["slug"] is not None
    assert body["title"] == "Test API Post"
    assert body["status"] == "published"
    assert body["url"] is not None


@pytest.mark.django_db
def test_publish_post_creates_draft():
    key = ApiKey.objects.create(name="Agent")
    client = Client()
    payload = {
        "title": "Draft Post",
        "description": "Draft via API",
        "content": "Draft content",
        "status": "draft",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    assert body["status"] == "draft"


@pytest.mark.django_db
def test_publish_post_returns_401_without_key():
    client = Client()
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps({"title": "X", "description": "Y", "content": "Z"}),
        content_type="application/json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_publish_post_validates_required_fields():
    key = ApiKey.objects.create(name="Agent")
    client = Client()
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps({"title": "Missing description"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 400
    body = json.loads(response.content)
    assert "error" in body or "errors" in body


@pytest.mark.django_db
def test_publish_post_with_timecodes():
    key = ApiKey.objects.create(name="Agent")
    client = Client()
    payload = {
        "title": "Video Post",
        "description": "Video via API",
        "content": "# Video\n\nDescription here.",
        "content_type": "video",
        "media_url": "https://example.com/video.mp4",
        "timecodes": [
            {"time": "0:00", "label": "Intro"},
            {"time": "1:30", "label": "Demo"},
        ],
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    assert body["content_type"] == "video"
    assert body["media_url"] == "https://example.com/video.mp4"


@pytest.mark.django_db
def test_publish_post_replaces_existing_with_flag():
    key = ApiKey.objects.create(name="Agent")
    client = Client()
    payload = {
        "title": "Replaceable Post",
        "description": "First version",
        "content": "v1",
    }
    r1 = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert r1.status_code == 201
    slug = json.loads(r1.content)["slug"]

    payload["description"] = "Second version"
    r2 = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert r2.status_code == 409

    payload["replace"] = True
    r3 = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert r3.status_code == 201
    body3 = json.loads(r3.content)
    assert body3["description"] == "Second version"


# ─── E2E: API → public site ───────────────────────────────────────────────────
# These tests verify the full cycle: agent POSTs via API → post appears on
# the public site (list + detail), drafts stay hidden, all content types render.

@pytest.mark.django_db
def test_e2e_published_post_appears_in_list_and_detail():
    """Post created via API shows on the public list and detail page."""
    from django.test import Client as PublicClient

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()
    payload = {
        "title": "E2E Visible Post",
        "description": "Should appear on the public site",
        "content": "# Hello\n\nPublic content here.",
        "tags": ["e2e"],
        "category": "E2E Tests",
        "status": "published",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    slug = body["slug"]

    # Post should appear in the public list
    list_response = client.get("/")
    assert list_response.status_code == 200
    assert "E2E Visible Post".encode() in list_response.content

    # Post detail page should render
    detail_response = client.get(f"/post/{slug}/")
    assert detail_response.status_code == 200
    assert "E2E Visible Post".encode() in detail_response.content
    assert "Should appear on the public site".encode() in detail_response.content


@pytest.mark.django_db
def test_e2e_draft_post_hidden_from_public():
    """Draft created via API does NOT appear on public list or detail."""
    from django.test import Client as PublicClient

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()
    payload = {
        "title": "E2E Hidden Draft",
        "description": "Should not be visible publicly",
        "content": "Secret draft content.",
        "status": "draft",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    slug = body["slug"]

    # Draft should NOT appear in the public list
    list_response = client.get("/")
    assert list_response.status_code == 200
    assert "E2E Hidden Draft".encode() not in list_response.content

    # Draft detail should 404
    detail_response = client.get(f"/post/{slug}/")
    assert detail_response.status_code == 404


@pytest.mark.django_db
def test_e2e_all_content_types_render_on_detail():
    """All 4 content types (article, video, audio, podcast) render on detail."""
    from django.test import Client as PublicClient

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()

    type_payloads = {
        "article": {
            "title": "E2E Article",
            "description": "Article description",
            "content": "# Article\n\nText content.",
            "content_type": "article",
        },
        "video": {
            "title": "E2E Video",
            "description": "Video description",
            "content": "# Video\n\nText content.",
            "content_type": "video",
            "media_url": "https://example.com/video.mp4",
            "timecodes": [
                {"time": "0:00", "label": "Intro"},
                {"time": "1:30", "label": "Demo"},
            ],
        },
        "audio": {
            "title": "E2E Audio",
            "description": "Audio description",
            "content": "# Audio\n\nText content.",
            "content_type": "audio",
            "media_url": "https://example.com/audio.mp3",
        },
        "podcast": {
            "title": "E2E Podcast",
            "description": "Podcast description",
            "content": "# Podcast\n\nText content.",
            "content_type": "podcast",
            "media_url": "https://example.com/podcast.opus",
            "timecodes": [
                {"time": "0:00", "label": "Start"},
                {"time": "5:00", "label": "Topic"},
            ],
        },
    }

    for content_type, payload in type_payloads.items():
        response = client.post(
            "/api/v1/posts/publish/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer " + key.token,
        )
        assert response.status_code == 201, f"Failed for {content_type}: {response.content}"
        body = json.loads(response.content)
        slug = body["slug"]

        # Verify the post exists in DB with correct content_type
        from blog.models import Post
        post = Post.objects.get(slug=slug)
        assert post.content_type == content_type, f"DB content_type mismatch for {content_type}"

        # Detail page renders
        detail_response = client.get(f"/post/{slug}/")
        assert detail_response.status_code == 200, f"Detail 404 for {content_type}"

        # For media types, verify media_url is rendered
        if content_type != "article":
            assert post.media_url == payload["media_url"], f"media_url mismatch for {content_type}"

        # For types with timecodes, verify they're stored
        if "timecodes" in payload:
            assert len(post.timecodes) == len(payload["timecodes"]), f"timecodes mismatch for {content_type}"
            assert post.timecodes[0]["label"] == payload["timecodes"][0]["label"]


@pytest.mark.django_db
def test_e2e_post_with_tags_and_category_on_detail():
    """Post created via API with tags and category renders them on detail."""
    from django.test import Client as PublicClient
    from blog.models import Category, Tag

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()
    payload = {
        "title": "E2E Tagged Post",
        "description": "Post with tags and category",
        "content": "Tagged content.",
        "tags": ["Python", "Django", "E2E"],
        "category": "Testing",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    slug = body["slug"]

    # Verify category and tags were created and linked
    assert Category.objects.filter(name="Testing").exists()
    assert Tag.objects.filter(name="Python").exists()
    assert Tag.objects.filter(name="Django").exists()
    assert Tag.objects.filter(name="E2E").exists()

    from blog.models import Post
    post = Post.objects.get(slug=slug)
    assert post.category.name == "Testing"
    tag_names = set(post.tags.values_list("name", flat=True))
    assert tag_names == {"Python", "Django", "E2E"}

    # Verify serialized response includes them
    assert body["category"] == "Testing"
    assert set(body["tags"]) == {"Python", "Django", "E2E"}


@pytest.mark.django_db
def test_e2e_replace_flag_updates_public_post():
    """Replace flag re-creates the post; old content gone, new content visible."""
    from django.test import Client as PublicClient

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()

    # Create v1
    payload = {
        "title": "E2E Replace Test",
        "description": "Version 1",
        "content": "Original content.",
    }
    r1 = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert r1.status_code == 201
    slug = json.loads(r1.content)["slug"]

    # Verify v1 on public site
    detail1 = client.get(f"/post/{slug}/")
    assert detail1.status_code == 200
    assert b"Version 1" in detail1.content

    # Attempt v2 without replace → 409
    payload["description"] = "Version 2"
    r2 = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert r2.status_code == 409

    # Replace with v2
    payload["replace"] = True
    r3 = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert r3.status_code == 201

    # Verify v2 on public site, v1 gone
    detail2 = client.get(f"/post/{slug}/")
    assert detail2.status_code == 200
    assert b"Version 2" in detail2.content
    assert b"Version 1" not in detail2.content


@pytest.mark.django_db
def test_e2e_invalid_content_type_defaults_to_article():
    """Invalid content_type falls back to article, not 400."""
    from django.test import Client as PublicClient
    from blog.models import Post

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()
    payload = {
        "title": "E2E Invalid Type",
        "description": "Bad content_type",
        "content": "Content.",
        "content_type": "nonexistent_type",
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    post = Post.objects.get(slug=body["slug"])
    assert post.content_type == "article"


@pytest.mark.django_db
def test_e2e_timecodes_have_seconds_field():
    """Timecodes posted via API include the 'seconds' field for player seek."""
    from django.test import Client as PublicClient
    from blog.models import Post

    key = ApiKey.objects.create(name="Agent")
    client = PublicClient()
    payload = {
        "title": "E2E Timecode Seconds",
        "description": "Verify seconds field",
        "content": "Content.",
        "content_type": "video",
        "media_url": "https://example.com/v.mp4",
        "timecodes": [
            {"time": "1:30", "label": "1m30s"},
            {"time": "2:57", "label": "2m57s"},
            {"time": "1:00:00", "label": "1h"},
        ],
    }
    response = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    post = Post.objects.get(slug=body["slug"])

    assert len(post.timecodes) == 3
    assert post.timecodes[0]["seconds"] == 90   # 1:30
    assert post.timecodes[1]["seconds"] == 177  # 2:57
    assert post.timecodes[2]["seconds"] == 3600 # 1:00:00
    assert post.timecodes[0]["label"] == "1m30s"