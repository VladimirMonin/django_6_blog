import pytest
from django.urls import reverse

from blog.models import Post


@pytest.fixture
def published_post(db):
    return Post.objects.create(
        title="Linux smoke test",
        content="**Проверка** Django 6 на Linux",
        is_published=True,
    )


@pytest.fixture
def draft_post(db):
    return Post.objects.create(
        title="Draft only",
        content="Черновик не должен быть виден публично",
        is_published=False,
    )


@pytest.mark.django_db
def test_post_generates_slug_with_django_fallback_for_latin_title():
    post = Post.objects.create(title="Linux smoke test", content="content")

    assert post.slug == "linux-smoke-test"


@pytest.mark.django_db
def test_post_converts_markdown_to_html_on_save():
    post = Post.objects.create(title="Markdown post", content="**strong text**")

    assert "<strong>strong text</strong>" in post.content_html


@pytest.mark.django_db
def test_post_list_renders_empty_database(client):
    response = client.get(reverse("post_list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_post_list_shows_published_posts_and_hides_drafts(client, published_post, draft_post):
    response = client.get(reverse("post_list"))

    assert response.status_code == 200
    assert published_post.title.encode() in response.content
    assert draft_post.title.encode() not in response.content


@pytest.mark.django_db
def test_post_search_filters_published_posts(client):
    matching = Post.objects.create(
        title="Django pytest guide",
        content="Текст про pytest-django",
        is_published=True,
    )
    hidden = Post.objects.create(
        title="Unrelated note",
        content="Другой текст",
        is_published=True,
    )

    response = client.get(reverse("post_list"), {"search": "pytest"})

    assert response.status_code == 200
    assert matching.title.encode() in response.content
    assert hidden.title.encode() not in response.content


@pytest.mark.django_db
def test_post_detail_renders_published_post(client, published_post):
    response = client.get(reverse("post_detail", kwargs={"pk": published_post.pk}))

    assert response.status_code == 200
    assert published_post.title.encode() in response.content


@pytest.mark.django_db
def test_post_detail_returns_404_for_draft(client, draft_post):
    response = client.get(reverse("post_detail", kwargs={"pk": draft_post.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_htmx_load_more_returns_card_partial(client, published_post):
    response = client.get(
        reverse("post_list"),
        {"load_more": "true"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert published_post.title.encode() in response.content


def test_about_and_admin_login_render(client):
    about_response = client.get(reverse("about"))
    admin_response = client.get("/admin/login/")

    assert about_response.status_code == 200
    assert admin_response.status_code == 200
