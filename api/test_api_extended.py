import json

import pytest
from django.test import Client

from api.models import ApiKey
from blog.models import Post


@pytest.fixture
def api_client():
    key = ApiKey.objects.create(name="API Extended Agent")
    client = Client()
    return client, key


@pytest.mark.django_db
def test_api_list_posts_with_filters_and_pagination(api_client):
    client, key = api_client
    Post.objects.create(
        title="Article 1",
        description="A1",
        content="body",
        slug="article-1",
        content_type=Post.ContentType.ARTICLE,
        status=Post.Status.PUBLISHED,
    )
    Post.objects.create(
        title="Video 1",
        description="V1",
        content="body",
        slug="video-1",
        content_type=Post.ContentType.VIDEO,
        media_url="https://example.com/video.mp4",
        status=Post.Status.DRAFT,
    )

    response = client.get(
        "/api/v1/posts/?content_type=video&status=draft&page=1&per_page=10",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["pagination"]["total_items"] == 1
    assert data["results"][0]["slug"] == "video-1"
    assert data["results"][0]["status"] == "draft"


@pytest.mark.django_db
def test_api_get_post_detail(api_client):
    client, key = api_client
    post = Post.objects.create(
        title="Detail API",
        description="desc",
        content="body",
        slug="detail-api",
        status=Post.Status.PUBLISHED,
    )
    response = client.get(
        f"/api/v1/posts/{post.slug}/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["slug"] == post.slug
    assert data["content"] == "body"


@pytest.mark.django_db
def test_api_patch_status_hides_and_restores_public_post(api_client):
    client, key = api_client
    post = Post.objects.create(
        title="Patch Status",
        description="desc",
        content="body",
        slug="patch-status",
        status=Post.Status.PUBLISHED,
    )

    patch_response = client.generic(
        "PATCH",
        f"/api/v1/posts/{post.slug}/status/",
        data=json.dumps({"status": "draft"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert patch_response.status_code == 200
    post.refresh_from_db()
    assert post.status == Post.Status.DRAFT

    public_client = Client()
    detail = public_client.get(f"/post/{post.slug}/")
    assert detail.status_code == 404

    restore_response = client.generic(
        "PATCH",
        f"/api/v1/posts/{post.slug}/status/",
        data=json.dumps({"status": "published"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert restore_response.status_code == 200
    post.refresh_from_db()
    assert post.status == Post.Status.PUBLISHED
    detail_again = public_client.get(f"/post/{post.slug}/")
    assert detail_again.status_code == 200


@pytest.mark.django_db
def test_api_delete_post_removes_it(api_client):
    client, key = api_client
    post = Post.objects.create(
        title="Delete Me",
        description="desc",
        content="body",
        slug="delete-me",
        status=Post.Status.PUBLISHED,
    )

    response = client.delete(
        f"/api/v1/posts/{post.slug}/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert response.status_code == 204
    # Soft delete: record still exists but marked as deleted
    assert not Post.objects.filter(slug=post.slug, deleted_at__isnull=True).exists()

    again = client.get(
        f"/api/v1/posts/{post.slug}/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert again.status_code == 404


@pytest.mark.django_db
def test_api_e2e_publish_list_detail_unpublish_delete(api_client):
    client, key = api_client
    payload = {
        "title": "Full Agent Cycle",
        "description": "full cycle",
        "content": "body",
        "content_type": "podcast",
        "media_url": "https://example.com/podcast.opus",
        "series": "Agent Workflows",
        "series_order": 1,
        "status": "published",
    }
    publish = client.post(
        "/api/v1/posts/publish/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert publish.status_code == 201
    slug = json.loads(publish.content)["slug"]

    listed = client.get(
        "/api/v1/posts/?content_type=podcast",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert listed.status_code == 200
    listed_data = json.loads(listed.content)
    assert any(item["slug"] == slug for item in listed_data["results"])

    detail = client.get(
        f"/api/v1/posts/{slug}/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert detail.status_code == 200
    detail_data = json.loads(detail.content)
    assert detail_data["series"] == "Agent Workflows"
    assert detail_data["series_order"] == 1

    unpublish = client.generic(
        "PATCH",
        f"/api/v1/posts/{slug}/status/",
        data=json.dumps({"status": "draft"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert unpublish.status_code == 200
    public_detail = Client().get(f"/post/{slug}/")
    assert public_detail.status_code == 404

    delete = client.delete(
        f"/api/v1/posts/{slug}/",
        HTTP_AUTHORIZATION="Bearer " + key.token,
    )
    assert delete.status_code == 204
    assert not Post.objects.filter(slug=slug, deleted_at__isnull=True).exists()
