from django.core.files.base import ContentFile
from django.urls import resolve, reverse
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup

from blog.models import Category, Post, PostMedia, Tag
from blog.views import AboutView, PostDetailView, PostLikeToggleView, PostListView

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def category():
    return Category.objects.create(name="Django", slug="django")


@pytest.fixture
def tag_python():
    return Tag.objects.create(name="Python", slug="python")


@pytest.fixture
def tag_uv():
    return Tag.objects.create(name="uv", slug="uv")


def create_post(title, content="Текст", *, status=Post.Status.PUBLISHED, category=None, tags=()):
    post = Post.objects.create(
        title=title,
        content=content,
        status=status,
        category=category,
    )
    if tags:
        post.tags.set(tags)
    return post


def soup(response):
    return BeautifulSoup(response.content, "html.parser")


@pytest.mark.django_db
def test_post_excerpt_strips_markdown_and_obsidian_embeds():
    post = create_post(
        "Токены, параметры и встраивания",
        content="""# Токены, параметры и встраивания 🧠

![[cover-01.webp]]

### 🎧 Подкаст
![[01_Как_нейросети_превращают_слова_в_геометрию.opus]]

Локальная языковая модель часто кажется магической.
> Небольшая цитата.
""",
    )

    excerpt = post.plain_text_excerpt

    assert "[[" not in excerpt
    assert "cover-01.webp" not in excerpt
    assert ".opus" not in excerpt
    assert "#" not in excerpt
    assert excerpt.startswith("🧠") or excerpt.startswith("Локальная")
    assert "Локальная языковая модель" in excerpt


@pytest.mark.django_db
def test_detail_page_does_not_duplicate_leading_title_heading(client):
    post = create_post(
        "Визуальная проверка статьи",
        content="# Визуальная проверка статьи\n\nТекст статьи",
    )

    response = client.get(post.get_absolute_url())

    assert response.status_code == 200
    page = soup(response)
    headings = [heading.get_text(strip=True) for heading in page.select("h1")]
    assert headings.count("Визуальная проверка статьи") == 1
    assert "Текст статьи" in response.content.decode()


@pytest.mark.django_db
def test_post_card_uses_first_image_as_cover(client):
    post = create_post("Пост с обложкой", content="Текст без markdown")
    media = PostMedia(post=post, original_filename="cover.webp")
    media.file.save("cover.webp", ContentFile(b"fake-image"), save=True)

    response = client.get("/")

    assert response.status_code == 200
    page = soup(response)
    cover = page.select_one("img.post-card-cover")
    assert cover is not None
    assert cover["alt"] == "Обложка статьи Пост с обложкой"


@pytest.mark.django_db
def test_public_list_shows_published_posts_and_hides_drafts(client):
    create_post("Опубликованный пост")
    create_post("Черновик", status=Post.Status.DRAFT)

    response = client.get("/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Опубликованный пост" in body
    assert "Черновик" not in body


@pytest.mark.django_db
def test_draft_detail_returns_404(client):
    draft = create_post("Закрытый черновик", status=Post.Status.DRAFT)

    response = client.get(draft.get_absolute_url())

    assert response.status_code == 404


@pytest.mark.django_db
def test_categories_and_tags_filter_public_posts(client, category, tag_python, tag_uv):
    matching = create_post("Django и uv", category=category, tags=[tag_python, tag_uv])
    create_post("Просто заметка")

    category_response = client.get("/", {"category": category.slug})
    tag_response = client.get("/", {"tag": tag_python.slug})

    assert category_response.status_code == 200
    assert matching.title in category_response.content.decode()
    assert "Просто заметка" not in category_response.content.decode()
    assert tag_response.status_code == 200
    assert matching.title in tag_response.content.decode()
    assert "Просто заметка" not in tag_response.content.decode()


@pytest.mark.django_db
def test_search_checks_title_content_category_and_tags(client, category, tag_python):
    create_post("Без слова в заголовке", content="обычный текст", category=category)
    create_post("Про backend", content="обычный текст", tags=[tag_python])
    create_post("Не подходит", content="ничего полезного")

    category_response = client.get("/", {"search": "Django"})
    tag_response = client.get("/", {"search": "Python"})

    assert category_response.status_code == 200
    assert "Без слова в заголовке" in category_response.content.decode()
    assert "Не подходит" not in category_response.content.decode()
    assert tag_response.status_code == 200
    assert "Про backend" in tag_response.content.decode()
    assert "Не подходит" not in tag_response.content.decode()


@pytest.mark.django_db
def test_search_uses_unicode_casefold_for_cyrillic(client):
    create_post("Визуальная проверка статьи", content="обычный текст")
    create_post("Не подходит", content="ничего полезного")

    response = client.get("/", {"search": "визуальная"})

    assert response.status_code == 200
    body = response.content.decode()
    assert "Визуальная проверка статьи" in body
    assert "Не подходит" not in body


@pytest.mark.django_db
def test_htmx_search_returns_partial_and_oob_paginator_with_encoded_load_more(client, category):
    for index in range(7):
        create_post(f"Django пост {index}", content="Django блог", category=category)

    response = client.get(
        "/",
        {"search": "Django блог"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    page = soup(response)
    assert page.select_one("html") is None
    paginator = page.select_one("#paginator-nav[hx-swap-oob='true']")
    assert paginator is not None
    load_more = page.select_one("button[hx-get*='load_more=true']")
    assert load_more is not None
    parsed = urlparse(load_more["hx-get"].lstrip("?"))
    params = parse_qs(parsed.path or parsed.query)
    assert params["search"] == ["Django блог"]
    assert params["load_more"] == ["true"]


@pytest.mark.django_db
def test_seo_paginator_links_preserve_filters_without_requiring_htmx(client, category, tag_python):
    for index in range(7):
        create_post(f"Django page {index}", category=category, tags=[tag_python])

    response = client.get("/", {"search": "Django", "category": category.slug, "tag": tag_python.slug})

    assert response.status_code == 200
    page = soup(response)
    next_link = page.select_one("a.page-link[href*='page=2']")
    assert next_link is not None
    href = next_link["href"]
    assert "search=Django" in href
    assert f"category={category.slug}" in href
    assert f"tag={tag_python.slug}" in href
    assert next_link["hx-get"] == href


def test_environment_example_documents_runtime_variables():
    env_example = PROJECT_ROOT / ".env.example"

    assert env_example.exists()
    content = env_example.read_text(encoding="utf-8")
    assert "DJANGO_SECRET_KEY=" in content
    assert "DJANGO_DEBUG=" in content
    assert "DJANGO_ALLOWED_HOSTS=" in content
    assert "DATABASE_URL" not in content


def test_public_blog_urls_are_class_based_views():
    assert resolve(reverse("post_list")).func.view_class is PostListView
    assert resolve(reverse("about")).func.view_class is AboutView
    assert resolve(reverse("post_detail", kwargs={"slug": "sample-post"})).func.view_class is PostDetailView
    assert resolve(reverse("post_like_toggle", kwargs={"slug": "sample-post"})).func.view_class is PostLikeToggleView


@pytest.mark.django_db
def test_detail_view_counts_one_view_per_anonymous_session(client):
    post = create_post("Счётчик просмотров", content="Текст")

    first = client.get(post.get_absolute_url())
    second = client.get(post.get_absolute_url())

    post.refresh_from_db()
    assert first.status_code == 200
    assert second.status_code == 200
    assert post.view_count == 1
    assert "1 просмотр" in second.content.decode()


@pytest.mark.django_db
def test_detail_view_counts_different_anonymous_sessions_separately(client, django_user_model):
    post = create_post("Просмотры из разных сессий", content="Текст")

    other_client = client.__class__()
    client.get(post.get_absolute_url())
    other_client.get(post.get_absolute_url())

    post.refresh_from_db()
    assert post.view_count == 2


@pytest.mark.django_db
def test_anonymous_like_toggle_is_stored_in_session_history(client):
    post = create_post("Лайк через сессию", content="Текст")
    like_url = reverse("post_like_toggle", kwargs={"slug": post.slug})

    liked = client.post(like_url, HTTP_HX_REQUEST="true")
    post.refresh_from_db()
    liked_page = soup(liked)
    liked_button = liked_page.select_one("button.post-like-button")

    assert liked.status_code == 200
    assert post.like_count == 1
    assert liked_button is not None
    assert "is-liked" in liked_button.get("class", [])
    assert liked_button["aria-pressed"] == "true"
    assert "1 лайк" in liked.content.decode()

    unliked = client.post(like_url, HTTP_HX_REQUEST="true")
    post.refresh_from_db()
    unliked_page = soup(unliked)
    unliked_button = unliked_page.select_one("button.post-like-button")

    assert unliked.status_code == 200
    assert post.like_count == 0
    assert unliked_button is not None
    assert "is-liked" not in unliked_button.get("class", [])
    assert unliked_button["aria-pressed"] == "false"
    assert "0 лайков" in unliked.content.decode()


@pytest.mark.django_db
def test_detail_page_renders_reaction_counters_and_like_form(client):
    post = create_post("Красивые реакции", content="Текст")
    post.view_count = 12
    post.like_count = 3
    post.save(update_fields=["view_count", "like_count"])

    response = client.get(post.get_absolute_url())

    assert response.status_code == 200
    page = soup(response)
    reactions = page.select_one(".post-reactions")
    button = page.select_one("button.post-like-button")
    assert reactions is not None
    assert button is not None
    assert button["hx-post"] == reverse("post_like_toggle", kwargs={"slug": post.slug})
    body = response.content.decode()
    assert "13 просмотров" in body
    assert "3 лайка" in body


@pytest.mark.django_db
def test_post_cards_render_view_and_like_counters(client):
    post = create_post("Карточка со счётчиками", content="Текст")
    post.view_count = 7
    post.like_count = 2
    post.save(update_fields=["view_count", "like_count"])

    response = client.get("/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "7 просмотров" in body
    assert "2 лайка" in body
