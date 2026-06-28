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