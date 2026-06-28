"""Tests for content analytics: PostView tracking, read-depth endpoint."""
import json
import pytest
from django.test import Client
from blog.models import Post, PostView


@pytest.fixture
def published_post():
    post = Post.objects.create(
        title="Analytics Test Post",
        description="Testing view tracking",
        content="# Hello\n\nSome content here.",
        slug="analytics-test-post",
        status=Post.Status.PUBLISHED,
    )
    return post


@pytest.mark.django_db
def test_read_depth_creates_post_view(published_post):
    """POST to read-depth endpoint creates a PostView record."""
    client = Client()
    response = client.post(
        f"/api/v1/posts/{published_post.slug}/read-depth/",
        data=json.dumps({"read_depth": 0.75}),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = json.loads(response.content)
    assert body["ok"] is True
    assert PostView.objects.filter(post=published_post).count() == 1
    pv = PostView.objects.get(post=published_post)
    assert pv.read_depth == 0.75


@pytest.mark.django_db
def test_read_depth_clamps_values(published_post):
    """Read depth values outside 0-1 are clamped."""
    client = Client()
    # Too high
    response = client.post(
        f"/api/v1/posts/{published_post.slug}/read-depth/",
        data=json.dumps({"read_depth": 5.0}),
        content_type="application/json",
    )
    assert response.status_code == 201
    pv = PostView.objects.get(post=published_post)
    assert pv.read_depth == 1.0

    # Negative
    PostView.objects.all().delete()
    response = client.post(
        f"/api/v1/posts/{published_post.slug}/read-depth/",
        data=json.dumps({"read_depth": -0.5}),
        content_type="application/json",
    )
    assert response.status_code == 201
    pv = PostView.objects.get(post=published_post)
    assert pv.read_depth == 0.0


@pytest.mark.django_db
def test_read_depth_rejects_get(published_post):
    """GET request to read-depth endpoint returns 405."""
    client = Client()
    response = client.get(f"/api/v1/posts/{published_post.slug}/read-depth/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_read_depth_returns_404_for_draft():
    """Read-depth endpoint only works for published posts."""
    draft = Post.objects.create(
        title="Draft",
        description="draft",
        content="content",
        slug="draft-post",
        status=Post.Status.DRAFT,
    )
    client = Client()
    response = client.post(
        f"/api/v1/posts/{draft.slug}/read-depth/",
        data=json.dumps({"read_depth": 0.5}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_read_depth_returns_404_for_soft_deleted(published_post):
    """Read-depth endpoint returns 404 for soft-deleted posts."""
    published_post.soft_delete()
    client = Client()
    response = client.post(
        f"/api/v1/posts/{published_post.slug}/read-depth/",
        data=json.dumps({"read_depth": 0.5}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_read_depth_no_api_key_required(published_post):
    """Read-depth endpoint does not require API key (public)."""
    client = Client()
    response = client.post(
        f"/api/v1/posts/{published_post.slug}/read-depth/",
        data=json.dumps({"read_depth": 0.5}),
        content_type="application/json",
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_post_view_string_representation(published_post):
    """PostView __str__ returns useful info."""
    pv = PostView.objects.create(
        post=published_post,
        session_key="testsessionkey123",
        read_depth=0.8,
    )
    s = str(pv)
    assert str(published_post.pk) in s


@pytest.mark.django_db
def test_post_view_admin_registration():
    """PostView is registered in admin."""
    from django.contrib import admin
    from blog.models import PostView
    assert PostView in admin.site._registry


@pytest.mark.django_db
def test_audit_log_admin_registration():
    """AuditLog is registered in admin."""
    from django.contrib import admin
    from blog.models import AuditLog
    assert AuditLog in admin.site._registry


@pytest.mark.django_db
def test_read_depth_invalid_json(published_post):
    """Invalid JSON returns 400."""
    client = Client()
    response = client.post(
        f"/api/v1/posts/{published_post.slug}/read-depth/",
        data="not json",
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_multiple_read_depth_records(published_post):
    """Multiple read-depth POSTs create multiple PostView records."""
    client = Client()
    for i in range(3):
        client.post(
            f"/api/v1/posts/{published_post.slug}/read-depth/",
            data=json.dumps({"read_depth": 0.3 * (i + 1)}),
            content_type="application/json",
        )
    assert PostView.objects.filter(post=published_post).count() == 3
    depths = list(PostView.objects.filter(post=published_post).values_list("read_depth", flat=True).order_by("read_depth"))
    assert abs(depths[0] - 0.3) < 0.01
    assert abs(depths[1] - 0.6) < 0.01
    assert abs(depths[2] - 0.9) < 0.01