from django.core.files.base import ContentFile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup

from blog.models import Category, Post, PostMedia, Tag

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
