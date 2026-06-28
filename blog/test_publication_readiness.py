from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from blog.models import Category, Post, Tag


PROJECT_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.django_db


def create_post(title, content="Текст публикации", *, category=None, tags=()):
    post = Post.objects.create(
        title=title,
        content=content,
        status=Post.Status.PUBLISHED,
        category=category,
    )
    if tags:
        post.tags.set(tags)
    return post


def soup(response):
    return BeautifulSoup(response.content, "html.parser")


def test_invalid_page_number_on_public_index_falls_back_to_safe_page(client):
    create_post("Публичный пост для пагинации")

    response = client.get("/", {"page": "not-a-number"})

    assert response.status_code == 200
    assert "Публичный пост для пагинации" in response.content.decode()


def test_unknown_category_or_tag_filter_returns_404(client):
    category_response = client.get("/", {"category": "missing-category"})
    tag_response = client.get("/", {"tag": "missing-tag"})

    assert category_response.status_code == 404
    assert tag_response.status_code == 404


def test_htmx_load_more_returns_only_next_cards_without_full_layout(client):
    category = Category.objects.create(name="Публикации", slug="publications")
    tag = Tag.objects.create(name="Личный блог", slug="personal-blog")
    for index in range(7):
        create_post(f"Материал {index}", category=category, tags=[tag])

    response = client.get(
        "/",
        {
            "category": category.slug,
            "tag": tag.slug,
            "page": "2",
            "load_more": "true",
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    page = soup(response)
    assert page.select_one("html") is None
    assert len(page.select(".post-card")) == 2
    titles = [link.get_text(strip=True) for link in page.select(".post-card-title-link")]
    assert titles == ["Материал 1", "Материал 0"]


def test_rendered_public_page_has_core_visual_landmarks(client):
    category = Category.objects.create(name="Заметки", slug="notes")
    tag = Tag.objects.create(name="Django", slug="django")
    create_post("Личный блог и статьи", category=category, tags=[tag])

    response = client.get("/")

    assert response.status_code == 200
    page = soup(response)
    assert page.select_one(".blog-hero h1") is not None
    assert page.select_one("form#post-filters input[type='search']") is not None
    assert page.select_one(".post-card") is not None
    assert page.select_one(".post-card-title-link").get_text(strip=True) == "Личный блог и статьи"
    assert page.select_one(".post-card-stats") is not None


def test_project_does_not_add_alternative_database_stack():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    settings = (PROJECT_ROOT / "config" / "settings.py").read_text(encoding="utf-8")

    # CI workflow is now intentionally present
    # Postgres/psycopg is still not part of this project stage
    assert "psycopg" not in pyproject
    assert "postgres" not in pyproject
    assert "DATABASE_URL" not in settings
    assert '"ENGINE": "django.db.backends.sqlite3"' in settings
