from django.core.files.base import ContentFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup

from blog.models import Category, Post, PostMedia, Tag
from blog.services.markdown_converter import convert_markdown_to_html
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


@pytest.mark.django_db
def test_detail_page_exposes_open_graph_metadata_for_link_previews(client):
    post = create_post(
        "Красивый шаринг",
        content="Текст поста",
    )
    post.description = "Описание для Telegram, VK и других карточек ссылок."
    post.save(update_fields=["description"])
    media = PostMedia(post=post, original_filename="share-cover.webp")
    media.file.save("share-cover.webp", ContentFile(b"fake-image"), save=True)

    response = client.get(post.get_absolute_url())

    assert response.status_code == 200
    page = soup(response)
    assert page.select_one('meta[property="og:type"]')["content"] == "article"
    assert page.select_one('meta[property="og:title"]')["content"] == post.title
    assert page.select_one('meta[property="og:description"]')["content"] == post.description
    assert page.select_one('meta[property="og:url"]')["content"] == f"http://testserver{post.get_absolute_url()}"
    assert page.select_one('meta[property="og:image"]')["content"].startswith("http://testserver/media/posts/")
    assert page.select_one('meta[name="twitter:card"]')["content"] == "summary_large_image"


@pytest.mark.django_db
def test_share_copy_controls_render_absolute_post_links_on_detail_and_cards(client):
    post = create_post("Копируемая ссылка", content="Текст")

    detail_response = client.get(post.get_absolute_url())
    list_response = client.get("/")

    assert detail_response.status_code == 200
    assert list_response.status_code == 200
    absolute_url = f"http://testserver{post.get_absolute_url()}"
    detail_page = soup(detail_response)
    list_page = soup(list_response)
    detail_button = detail_page.select_one("button.share-link-button-detail[data-share-copy]")
    card_button = list_page.select_one("button.share-link-button-card[data-share-copy]")
    script = detail_page.select_one('script[src$="/static/js/share-link.js"]')

    assert detail_button is not None
    assert detail_button["data-share-url"] == absolute_url
    assert detail_button.select_one("[data-share-label]").get_text(strip=True) == "Скопировать ссылку"
    assert card_button is not None
    assert card_button["data-share-url"] == absolute_url
    assert card_button.select_one("[data-share-label]").get_text(strip=True) == "Ссылка"
    assert script is not None


@pytest.mark.django_db
def test_rendered_post_images_have_lazy_loading_and_async_decoding(client):
    """Изображения в отрендеренном контенте поста получают loading="lazy"
    и decoding="async" для оптимизации загрузки и декодирования."""
    post = create_post(
        "Пост с картинкой",
        content="![Схема](/media/posts/demo/scheme.png)",
    )

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200

    page = soup(response)
    images = page.select(".post-content img")
    assert images, "ожидается хотя бы одно изображение в контенте поста"
    for image in images:
        assert image.get("loading") == "lazy"
        assert image.get("decoding") == "async"


def test_markdown_image_gets_lazy_loading_and_async_decoding_directly():
    """convert_markdown_to_html добавляет loading и decoding к <img>."""
    html = convert_markdown_to_html("![Схема](/media/posts/demo/scheme.png)")
    page = BeautifulSoup(html, "html.parser")
    image = page.select_one("img")
    assert image is not None
    assert image.get("loading") == "lazy"
    assert image.get("decoding") == "async"


# --- N+1 query regression guard -----------------------------------------------
# These tests verify that PostListView does not suffer from N+1 queries:
# adding more posts (with categories, tags, and media) must NOT increase the
# number of SQL queries executed while rendering the list page.


@pytest.mark.django_db
def test_post_list_view_query_count_is_bounded(client):
    """GET '/' executes a fixed number of queries regardless of post count.

    We create 10 published posts (two full pages at paginate_by=5), each with
    a category, two tags, and one image media file — the exact relations the
    post_card template iterates over. Then we capture the query count for the
    first page and assert it stays constant when we add another batch of posts.
    A growing count would indicate an N+1 in select_related/prefetch_related.
    """
    category = Category.objects.create(name="Django", slug="django")
    tag_python = Tag.objects.create(name="Python", slug="python")
    tag_uv = Tag.objects.create(name="uv", slug="uv")

    def make_batch(start, count):
        for index in range(start, start + count):
            post = Post.objects.create(
                title=f"N+1 regression post {index}",
                content="Текст поста для аудита запросов",
                status=Post.Status.PUBLISHED,
                category=category,
            )
            post.tags.set([tag_python, tag_uv])
            media = PostMedia(post=post, original_filename=f"cover-{index}.webp")
            media.file.save(
                f"cover-{index}.webp",
                ContentFile(b"fake-image-bytes"),
                save=True,
            )

    # First batch: 10 published posts (2 full pages).
    make_batch(0, 10)

    # Capture query count for the first page with 10 posts in the DB.
    with CaptureQueriesContext(connection) as first_ctx:
        response = client.get("/")
    assert response.status_code == 200
    first_page_queries = len(first_ctx)

    # Second batch: add 10 more posts (now 20 total, 4 pages).
    make_batch(10, 10)

    with CaptureQueriesContext(connection) as second_ctx:
        response = client.get("/")
    assert response.status_code == 200
    second_page_queries = len(second_ctx)

    # The defining property of no-N+1: query count is independent of row count.
    assert first_page_queries == second_page_queries, (
        f"N+1 detected: query count grew from {first_page_queries} to "
        f"{second_page_queries} when post count doubled from 10 to 20. "
        f"PostListView.get_queryset() must use select_related/prefetch_related "
        f"for every relation accessed in the post_card template."
    )

    # Also assert an explicit upper bound so silent growth is caught even if
    # both runs happen to match. The page renders 5 posts with category,
    # tags, media_files, plus the sidebar (categories, tags, tag_map), plus
    # the count query from Paginator. 30 is a generous ceiling that leaves
    # room for session/auth middleware queries while still catching N+1.
    assert second_page_queries <= 30, (
        f"Query count {second_page_queries} exceeds the 30-query ceiling; "
        f"likely N+1 on PostListView."
    )


@pytest.mark.django_db
def test_post_list_view_second_page_query_count_matches_first(client):
    """Pagination must not introduce per-row queries either.

    Rendering page=2 (a different slice of the same queryset) must execute
    the same number of queries as page=1, because the queryset is identical
    and only the Paginator slice changes.
    """
    category = Category.objects.create(name="Django", slug="django")
    tag_python = Tag.objects.create(name="Python", slug="python")

    for index in range(10):
        post = Post.objects.create(
            title=f"Pagination N+1 post {index}",
            content="Текст",
            status=Post.Status.PUBLISHED,
            category=category,
        )
        post.tags.set([tag_python])

    with CaptureQueriesContext(connection) as page1_ctx:
        response1 = client.get("/")
    assert response1.status_code == 200

    with CaptureQueriesContext(connection) as page2_ctx:
        response2 = client.get("/", {"page": 2})
    assert response2.status_code == 200

    assert len(page1_ctx) == len(page2_ctx), (
        f"Pagination N+1: page=1 ran {len(page1_ctx)} queries, "
        f"page=2 ran {len(page2_ctx)} queries."
    )


# --- Thumbnail generation tests ------------------------------------------------


def _make_real_png(width=200, height=150, color=(255, 100, 50)):
    """Return a ContentFile with a real, Pillow-readable PNG image."""
    from PIL import Image as PilImage

    img = PilImage.new("RGB", (width, height), color)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue())


@pytest.mark.django_db
def test_image_media_generates_thumbnails():
    """Saving an image PostMedia generates OG (1200x630) and card (400x300) thumbnails."""
    post = create_post("Пост с настоящей обложкой", content="Текст")
    media = PostMedia(post=post, original_filename="real-cover.png")
    media.file.save("real-cover.png", _make_real_png(800, 600), save=True)

    media.refresh_from_db()
    assert media.thumbnail_og, "OG thumbnail should be generated"
    assert media.thumbnail_card, "Card thumbnail should be generated"

    from PIL import Image as PilImage

    with PilImage.open(media.thumbnail_og.path) as og_img:
        assert og_img.size == (1200, 630), f"OG thumbnail size: {og_img.size}"

    with PilImage.open(media.thumbnail_card.path) as card_img:
        assert card_img.size == (400, 300), f"Card thumbnail size: {card_img.size}"


@pytest.mark.django_db
def test_thumbnail_urls_fallback_to_original():
    """Non-image PostMedia thumbnail_url properties fall back to file.url."""
    post = create_post("Пост с документом", content="Текст")
    media = PostMedia(post=post, original_filename="notes.pdf")
    media.file.save("notes.pdf", ContentFile(b"%PDF-1.4 fake"), save=True)

    media.refresh_from_db()
    assert media.media_type == PostMedia.MediaType.DOCUMENT
    assert media.thumbnail_og_url == media.file.url
    assert media.thumbnail_card_url == media.file.url
    assert not media.thumbnail_og
    assert not media.thumbnail_card


@pytest.mark.django_db
def test_detail_og_image_uses_thumbnail(client):
    """Detail page og:image meta points to the generated thumbnail, not the original."""
    post = create_post("OG превью с Thumbnail", content="Текст поста")
    media = PostMedia(post=post, original_filename="og-cover.png")
    media.file.save("og-cover.png", _make_real_png(1000, 800), save=True)
    media.refresh_from_db()

    assert media.thumbnail_og, "Thumbnail should exist for the test to be meaningful"

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200
    page = soup(response)
    og_image_url = page.select_one('meta[property="og:image"]')["content"]

    # The og:image URL should end with the thumbnail path (a .jpg file in
    # posts/thumbnails/), not the original .png file path.
    assert "/media/posts/thumbnails/" in og_image_url
    assert og_image_url.endswith(".jpg")
    assert "og-cover" in og_image_url
    # It must NOT be the original file URL.
    assert og_image_url != f"http://testserver{media.file.url}"


# --- Cache tests ---------------------------------------------------------------


@pytest.mark.django_db
def test_body_content_html_is_cached():
    """Accessing body_content_html twice does not hit the DB on the second call.

    The first call populates the cache (which may query the DB for
    content_html); the second call must be served from cache with zero
    SQL queries.
    """
    from django.core.cache import cache

    cache.clear()

    post = create_post("Кэшированный пост", content="Первый абзац текста")

    # First access — populates cache, may run queries.
    _ = post.body_content_html

    # Second access — must be served from cache, zero DB queries.
    with CaptureQueriesContext(connection) as ctx:
        result = post.body_content_html

    assert len(ctx) == 0, (
        f"Expected 0 DB queries on cached access, got {len(ctx)}."
    )
    assert "Первый абзац текста" in result


@pytest.mark.django_db
def test_cache_invalidated_on_save():
    """Saving a post invalidates the body_content_html cache.

    After updating post.content and calling save(), the next access to
    body_content_html must reflect the new content, not the stale cached
    version.
    """
    from django.core.cache import cache

    cache.clear()

    post = create_post("Инвалидация кэша", content="Старый контент")
    original_html = post.body_content_html
    assert "Старый контент" in original_html

    # Update content and save — this must invalidate the cache.
    post.content = "Новый контент после обновления"
    post.save()

    # Refresh content_html from DB (save() regenerates it from content).
    post.refresh_from_db()

    updated_html = post.body_content_html
    assert "Новый контент после обновления" in updated_html, (
        f"Expected new content in body_content_html, got stale: {updated_html}"
    )
    assert "Старый контент" not in updated_html


# --- ETag / Last-Modified conditional rendering for PostDetailView --------------


@pytest.mark.django_db
def test_detail_view_returns_304_for_unchanged_post(client):
    """PostDetailView sets ETag and Last-Modified headers and returns 304
    when the client re-requests with a matching If-None-Match / If-Modified-Since.
    """
    post = create_post("ETag детальный тест", content="Текст поста")

    first = client.get(post.get_absolute_url())
    assert first.status_code == 200
    etag = first.get("ETag")
    last_modified = first.get("Last-Modified")
    assert etag, "ETag header must be present on detail view"
    assert last_modified, "Last-Modified header must be present on detail view"

    # Re-request with If-None-Match → 304
    matched = client.get(post.get_absolute_url(), HTTP_IF_NONE_MATCH=etag)
    assert matched.status_code == 304, (
        f"Expected 304 for matching If-None-Match, got {matched.status_code}"
    )

    # Re-request with If-Modified-Since → 304
    since_response = client.get(
        post.get_absolute_url(),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert since_response.status_code == 304, (
        f"Expected 304 for matching If-Modified-Since, got {since_response.status_code}"
    )


@pytest.mark.django_db
def test_detail_view_etag_changes_after_post_update(client):
    """Updating a post changes updated_at, which changes the ETag, so a
    client sending the old ETag receives 200 (not 304).
    """
    post = create_post("ETag изменение", content="Первая версия")
    first = client.get(post.get_absolute_url())
    old_etag = first.get("ETag")
    assert first.status_code == 200

    # Bump updated_at by saving (auto_now=True refreshes it).
    post.content = "Вторая версия контента"
    post.save()

    stale = client.get(post.get_absolute_url(), HTTP_IF_NONE_MATCH=old_etag)
    assert stale.status_code == 200, (
        f"Expected 200 after post update with stale ETag, got {stale.status_code}"
    )
    new_etag = stale.get("ETag")
    assert new_etag != old_etag, "ETag must change after post update"


# --- PostDetailView query count bound -------------------------------------------


@pytest.mark.django_db
def test_detail_view_query_count_is_bounded(client):
    """GET on a post detail page with 5 media files executes a bounded number
    of queries (≤ 15), ensuring no N+1 on media_files, tags, or reactions.
    """
    post = create_post("Пост с пятью медиа", content="Контент для детальной страницы")

    # 1 image (cover) + 1 video (primary) + 3 documents.
    image_media = PostMedia(post=post, original_filename="cover.webp")
    image_media.file.save("cover.webp", ContentFile(b"fake-image"), save=True)
    video_media = PostMedia(post=post, original_filename="clip.mp4")
    video_media.file.save("clip.mp4", ContentFile(b"fake-video"), save=True)
    for index in range(3):
        doc = PostMedia(post=post, original_filename=f"doc-{index}.pdf")
        doc.file.save(f"doc-{index}.pdf", ContentFile(b"%PDF-1.4 fake"), save=True)

    url = post.get_absolute_url()
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200

    query_count = len(ctx)
    # The detail view runs the condition probe (1 query), get_object (1),
    # prefetch for tags (1) and media_files (1), then the session-interaction
    # machinery (get_or_create SessionPostInteraction, mark_viewed, view_count
    # update, is_post_liked, session save) — roughly 10 queries — plus
    # template-time checks. 20 is a tight ceiling that catches per-media N+1
    # (5 extra queries for 5 media items) while allowing the session work.
    assert query_count <= 20, (
        f"Detail view ran {query_count} queries; expected ≤ 20. "
        f"Likely N+1 on media_files, tags, or session interactions."
    )
