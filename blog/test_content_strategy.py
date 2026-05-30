from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.urls import resolve, reverse

from blog.content_import.obsidian import import_obsidian_note_to_post
from blog.models import Post, Tag
from blog.views import PostDetailView, PostLikeToggleView


pytestmark = pytest.mark.django_db


def create_post(title, content="Текст публикации", *, tags=()):
    post = Post.objects.create(
        title=title,
        description="Короткое описание публикации",
        content=content,
        status=Post.Status.PUBLISHED,
    )
    if tags:
        post.tags.set(tags)
    return post


def soup(response):
    return BeautifulSoup(response.content, "html.parser")


def test_importer_uses_first_h1_as_title_and_removes_duplicate_heading(tmp_path):
    note_path = tmp_path / "agent-generated-note.md"
    note_path.write_text(
        """---
description: Описание для карточки
---
# Агентский заголовок

Основной текст статьи.
""",
        encoding="utf-8",
    )

    post = import_obsidian_note_to_post(note_path)

    assert post.title == "Агентский заголовок"
    assert not post.content.lstrip().startswith("# Агентский заголовок")
    assert "<h1" not in post.content_html
    assert "Основной текст статьи" in post.content


def test_importer_prefers_explicit_title_and_still_removes_matching_h1(tmp_path):
    note_path = tmp_path / "note.md"
    note_path.write_text(
        """---
title: Явный заголовок
description: Описание для карточки
---
# Явный заголовок

Текст после заголовка.
""",
        encoding="utf-8",
    )

    post = import_obsidian_note_to_post(note_path)

    assert post.title == "Явный заголовок"
    assert post.content == "Текст после заголовка."


def test_public_detail_routes_use_slug_not_numeric_identifier(client):
    post = create_post("SEO адрес без ID")

    detail_url = reverse("post_detail", kwargs={"slug": post.slug})
    like_url = reverse("post_like_toggle", kwargs={"slug": post.slug})
    detail_response = client.get(detail_url)
    numeric_response = client.get(f"/post/{post.pk}/")

    assert detail_url == f"/post/{post.slug}/"
    assert resolve(detail_url).func.view_class is PostDetailView
    assert resolve(like_url).func.view_class is PostLikeToggleView
    assert detail_response.status_code == 200
    assert numeric_response.status_code == 404
    assert f"Пост #{post.pk}" not in detail_response.content.decode()


def test_detail_page_renders_author_and_server_side_breadcrumbs(client):
    post = create_post("Хлебные крошки и автор")

    response = client.get(post.get_absolute_url())

    assert response.status_code == 200
    page = soup(response)
    breadcrumb = page.select_one("nav[aria-label='Хлебные крошки'] ol.breadcrumb")
    assert breadcrumb is not None
    crumbs = [item.get_text(" ", strip=True) for item in breadcrumb.select("li")]
    assert crumbs == ["Главная", "Хлебные крошки и автор"]
    body = response.content.decode()
    assert "Автор: Владимир Монин" in body
    assert "Владимир Монин" in page.select_one("footer").get_text(" ", strip=True)


def test_index_renders_tag_map_with_public_post_counts(client):
    django = Tag.objects.create(name="Django", slug="django")
    uv = Tag.objects.create(name="uv", slug="uv")
    create_post("Первый пост", tags=[django, uv])
    create_post("Второй пост", tags=[django])
    Post.objects.create(
        title="Черновик",
        description="Описание",
        content="Текст",
        status=Post.Status.DRAFT,
    ).tags.set([uv])

    response = client.get("/")

    assert response.status_code == 200
    page = soup(response)
    tag_map = page.select_one("section.tag-map")
    assert tag_map is not None
    tags = {link.get_text(" ", strip=True): link["href"] for link in tag_map.select("a")}
    assert "#Django 2" in tags
    assert "#uv 1" in tags
    assert tags["#Django 2"].startswith("/?tag=django")
