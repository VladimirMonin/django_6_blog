import importlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import clear_url_caches, reverse

from blog.models import Post, PostMedia
from blog.services.markdown_media_preprocessor import MarkdownMediaPreprocessor


@pytest.fixture
def published_post(db):
    return Post.objects.create(
        title="Linux smoke test",
        content="**Проверка** Django 6 на Linux",
        status=Post.Status.PUBLISHED,
    )


@pytest.fixture
def draft_post(db):
    return Post.objects.create(
        title="Draft only",
        content="Черновик не должен быть виден публично",
        status=Post.Status.DRAFT,
    )


def _same_site_rendered_hrefs(response, source_path):
    soup = BeautifulSoup(response.content, "html.parser")
    hrefs = []
    for link in soup.select("a[href]"):
        href = link["href"].strip()
        parsed = urlparse(href)
        if (
            not href
            or href.startswith(("#", "mailto:", "tel:", "javascript:"))
            or parsed.scheme in {"http", "https"}
            or parsed.netloc
        ):
            continue
        absolute = urljoin(source_path, href)
        hrefs.append(absolute)
    return hrefs


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
        status=Post.Status.PUBLISHED,
    )
    hidden = Post.objects.create(
        title="Unrelated note",
        content="Другой текст",
        status=Post.Status.PUBLISHED,
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
def test_htmx_search_returns_partial_post_list(client):
    matching = Post.objects.create(
        title="Django HTMX partial",
        content="Материал про динамическую загрузку",
        status=Post.Status.PUBLISHED,
    )
    hidden = Post.objects.create(
        title="Plain Django page",
        content="Материал без нужного слова",
        status=Post.Status.PUBLISHED,
    )

    response = client.get(
        reverse("post_list"),
        {"search": "HTMX"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert b"<html" not in response.content.lower()
    assert matching.title.encode() in response.content
    assert hidden.title.encode() not in response.content
    assert b'id="paginator-nav"' in response.content


@pytest.mark.django_db
def test_load_more_button_preserves_search_query_as_urlencoded_parameter(client):
    for index in range(6):
        Post.objects.create(
            title=f"Django HTMX article {index}",
            content="Материал про автозагрузку карточек",
            status=Post.Status.PUBLISHED,
        )

    response = client.get(reverse("post_list"), {"search": "Django HTMX"})

    assert response.status_code == 200
    assert b"?page=2&amp;search=Django+HTMX&amp;load_more=true" in response.content


@pytest.mark.django_db
def test_htmx_load_more_returns_next_page_cards_only(client):
    for index in range(6):
        Post.objects.create(
            title=f"Autoload post {index}",
            content="Проверка второй страницы автозагрузки",
            status=Post.Status.PUBLISHED,
        )

    response = client.get(
        reverse("post_list"),
        {"page": "2", "load_more": "true"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert b"<html" not in response.content.lower()
    assert len(response.context["posts"]) == 1
    assert b"Autoload post" in response.content
    assert b'id="paginator-nav"' in response.content



def test_media_settings_are_configured_for_uploads():
    assert settings.MEDIA_URL == "/media/"
    assert settings.MEDIA_ROOT == settings.BASE_DIR / "media"


@pytest.mark.django_db
def test_post_media_upload_saves_file_metadata_to_database(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    post = Post.objects.create(title="Media DB smoke", content="Content")
    upload = SimpleUploadedFile("Screenshot One.PNG", b"image-bytes", content_type="image/png")

    media = PostMedia.objects.create(post=post, file=upload)

    assert media.pk is not None
    assert media.original_filename == "Screenshot One.PNG"
    assert media.file_slug == "screenshot-one.png"
    assert media.media_type == PostMedia.MediaType.IMAGE
    assert media.file.name == "posts/media-db-smoke/screenshot-one.png"
    assert media.file.storage.exists(media.file.name)


@pytest.mark.django_db
def test_markdown_media_preprocessor_resolves_obsidian_and_markdown_local_links(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    post = Post.objects.create(title="Media Links", content="Draft")
    image = PostMedia.objects.create(
        post=post,
        file=SimpleUploadedFile("diagram one.png", b"png", content_type="image/png"),
    )
    video = PostMedia.objects.create(
        post=post,
        file=SimpleUploadedFile("demo.mp4", b"mp4", content_type="video/mp4"),
    )
    markdown = "\n".join(
        [
            "![[diagram one.png|Architecture diagram]]",
            "![Demo clip](./demo.mp4)",
            "![External](https://example.com/external.png)",
            "![Missing](missing.png)",
        ]
    )

    converted = MarkdownMediaPreprocessor(post).process(markdown)

    assert f"![Architecture diagram]({image.file.url})" in converted
    assert f"![Demo clip]({video.file.url})" in converted
    assert "![External](https://example.com/external.png)" in converted
    assert "![Missing](missing.png)" in converted


@pytest.mark.django_db
def test_post_save_converts_media_links_to_rendered_html(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    post = Post.objects.create(title="Rendered media", content="Initial")
    media = PostMedia.objects.create(
        post=post,
        file=SimpleUploadedFile("hero.png", b"png", content_type="image/png"),
    )

    post.content = "![[hero.png|Hero image]]"
    post.save()

    post.refresh_from_db()
    assert f'src="{media.file.url}"' in post.content_html
    assert 'alt="Hero image"' in post.content_html


@pytest.mark.django_db
def test_admin_post_change_page_contains_media_upload_prototype(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password",
    )
    client.force_login(user)
    post = Post.objects.create(title="Admin uploader", content="Content")
    media = PostMedia.objects.create(
        post=post,
        file=SimpleUploadedFile("admin-preview.png", b"png", content_type="image/png"),
    )

    response = client.get(reverse("admin:blog_post_change", args=[post.pk]))

    assert response.status_code == 200
    assert b"media_files-0-file" in response.content
    assert media.markdown_link.encode() in response.content


@override_settings(DEBUG=True)
def test_media_file_is_served_in_debug_mode(client):
    import config.urls

    clear_url_caches()
    importlib.reload(config.urls)

    media_file = settings.MEDIA_ROOT / "smoke.txt"
    media_file.write_text("Hello Media", encoding="utf-8")

    try:
        response = client.get("/media/smoke.txt")
    finally:
        media_file.unlink(missing_ok=True)

    assert response.status_code == 200
    assert b"Hello Media" in b"".join(response.streaming_content)


def test_about_and_admin_login_render(client):
    about_response = client.get(reverse("about"))
    admin_response = client.get("/admin/login/")

    assert about_response.status_code == 200
    assert admin_response.status_code == 200


@pytest.mark.django_db
def test_rendered_public_internal_links_resolve_to_available_pages(client):
    posts = [
        Post.objects.create(
            title=f"Rendered links post {index}",
            content="Проверка ссылок из отрендеренного HTML",
            status=Post.Status.PUBLISHED,
        )
        for index in range(6)
    ]
    source_paths = [
        reverse("post_list"),
        reverse("about"),
        reverse("post_detail", kwargs={"pk": posts[0].pk}),
    ]
    discovered_hrefs = set()

    for source_path in source_paths:
        response = client.get(source_path)
        assert response.status_code == 200
        discovered_hrefs.update(_same_site_rendered_hrefs(response, source_path))

    assert discovered_hrefs
    for href in sorted(discovered_hrefs):
        response = client.get(href)
        assert response.status_code < 400, f"Rendered link {href!r} returned {response.status_code}"


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_rendered_post_media_sources_are_served_in_debug_mode(client, settings, tmp_path):
    import config.urls

    settings.MEDIA_ROOT = tmp_path
    clear_url_caches()
    importlib.reload(config.urls)

    post = Post.objects.create(title="Rendered media link", content="Initial")
    media = PostMedia.objects.create(
        post=post,
        file=SimpleUploadedFile("linked-image.png", b"image-bytes", content_type="image/png"),
    )
    post.content = "![[linked-image.png|Linked image]]"
    post.save()

    response = client.get(reverse("post_detail", kwargs={"pk": post.pk}))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    media_sources = [img["src"] for img in soup.select("img[src]")]

    assert media.file.url in media_sources
    media_response = client.get(media.file.url)
    assert media_response.status_code == 200
    assert b"image-bytes" in b"".join(media_response.streaming_content)


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_obsidian_lm_studio_lesson_fixture_imports_and_renders_media(client, settings, tmp_path):
    from blog.services.obsidian_importer import import_obsidian_note_to_post

    fixture_dir = Path(settings.BASE_DIR) / "tests/assets/obsidian/lm-studio/lesson-01"
    note_path = fixture_dir / "01-токены-параметры-и-встраивания.md"
    if not note_path.exists():
        pytest.skip("local Obsidian LM Studio fixture is not available")

    settings.MEDIA_ROOT = tmp_path
    clear_url_caches()
    import config.urls
    importlib.reload(config.urls)

    post = import_obsidian_note_to_post(note_path, assets_dir=fixture_dir)

    assert post.title == "Токены, параметры и встраивания"
    assert PostMedia.objects.filter(post=post).count() == 9
    assert PostMedia.objects.filter(post=post, media_type=PostMedia.MediaType.IMAGE).count() == 8
    assert PostMedia.objects.filter(post=post, media_type=PostMedia.MediaType.AUDIO).count() == 1

    response = client.get(reverse("post_detail", kwargs={"pk": post.pk}))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")

    image_sources = [img["src"] for img in soup.select("img[src]")]
    audio_sources = [audio["src"] for audio in soup.select("audio[src]")]

    assert len(image_sources) >= 8
    assert len(audio_sources) == 1
    assert audio_sources[0].endswith(".opus")
    assert not soup.select('img[src$=".opus"]')

    for media in PostMedia.objects.filter(post=post):
        media_response = client.get(media.file.url)
        assert media_response.status_code == 200, media.file.url
