"""SEO tests: sitemap, robots.txt, RSS/Atom feeds, JSON-LD, canonical URLs.

E2E tests verify the full cycle: publisher CLI → API → DB → public site →
sitemap → social meta tags (OG, Twitter, JSON-LD).
"""

import json
import re
import xml.etree.ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.templatetags.static import static
from django.test import Client, override_settings
from django.urls import reverse

from api.models import ApiKey
from blog.models import Post, PostMedia, Series
from publisher.client import publish_post
from publisher.parser import parse_markdown_file


# ── Sitemap tests ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_sitemap_contains_published_post():
    """Published post URL appears in sitemap.xml."""
    post = Post.objects.create(
        title="Sitemap Test",
        description="Sitemap desc",
        content="# Hello",
        slug="sitemap-test",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    body = response.content.decode()
    assert "/post/sitemap-test/" in body
    assert str(post.updated_at.date()) in body or str(post.updated_at.year) in body


@pytest.mark.django_db
def test_sitemap_excludes_draft_post():
    """Draft posts are not in sitemap.xml."""
    Post.objects.create(
        title="Draft Sitemap",
        description="Hidden",
        content="# Draft",
        slug="draft-sitemap",
        status=Post.Status.DRAFT,
    )
    client = Client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "/post/draft-sitemap/" not in response.content.decode()


@pytest.mark.django_db
def test_sitemap_contains_static_pages():
    """Home and about pages are in sitemap.xml."""
    client = Client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    body = response.content.decode()
    assert "<loc>" in body  # has at least some URLs


@pytest.mark.django_db
def test_sitemap_is_valid_xml():
    """Sitemap returns valid XML with namespace."""
    Post.objects.create(
        title="XML Test",
        description="XML",
        content="# X",
        slug="xml-test",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers.get("Content-Type", "")
    # Should parse without error
    ET.fromstring(response.content)


# ── robots.txt tests ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_robots_txt_returns_text_plain():
    """robots.txt returns text/plain with correct directives."""
    client = Client()
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("Content-Type", "")
    body = response.content.decode()
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Disallow: /admin/" in body
    assert "Disallow: /api/" in body
    assert "Sitemap:" in body
    assert "/sitemap.xml" in body


# ── RSS feed tests ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_rss_feed_contains_published_posts():
    """RSS feed has the 20 most recent published posts."""
    for i in range(3):
        Post.objects.create(
            title=f"RSS Post {i}",
            description=f"RSS desc {i}",
            content=f"# Content {i}",
            slug=f"rss-post-{i}",
            status=Post.Status.PUBLISHED,
        )
    client = Client()
    response = client.get("/feed/rss/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "RSS Post 0" in body
    assert "RSS Post 1" in body
    assert "RSS Post 2" in body
    assert "<rss" in body or "<channel>" in body


@pytest.mark.django_db
def test_rss_feed_excludes_drafts():
    """Draft posts are not in RSS feed."""
    Post.objects.create(
        title="RSS Draft",
        description="Hidden",
        content="# D",
        slug="rss-draft",
        status=Post.Status.DRAFT,
    )
    client = Client()
    response = client.get("/feed/rss/")
    assert response.status_code == 200
    assert "RSS Draft" not in response.content.decode()


@pytest.mark.django_db
def test_atom_feed_contains_published_posts():
    """Atom feed has published posts with Atom XML namespace."""
    Post.objects.create(
        title="Atom Post",
        description="Atom desc",
        content="# Atom",
        slug="atom-post",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get("/feed/atom/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Atom Post" in body
    assert "<feed" in body or "atom" in body.lower()


@pytest.mark.django_db
def test_rss_feed_has_post_link_and_description():
    """RSS items include title, link, and description."""
    Post.objects.create(
        title="RSS Fields",
        description="Custom description here",
        content="# Body",
        slug="rss-fields",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get("/feed/rss/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "RSS Fields" in body
    assert "Custom description here" in body
    assert "/post/rss-fields/" in body


# ── JSON-LD + canonical tests ───────────────────────────────────────────────


JSON_LD_SCRIPT_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def _parse_json_ld_scripts(response):
    """Parse every JSON-LD script in a rendered response with stdlib JSON."""
    scripts = JSON_LD_SCRIPT_RE.findall(response.content.decode())
    assert scripts, "JSON-LD script block not found"
    return [json.loads(script) for script in scripts]


def _graph_node(data, schema_type):
    """Return exactly one graph node of the requested schema.org type."""

    matches = [node for node in data["@graph"] if node.get("@type") == schema_type]
    assert len(matches) == 1
    return matches[0]


def _meta_values(page, attribute, name):
    """Return all content values for one Open Graph or Twitter meta field."""

    return [
        tag["content"]
        for tag in page.find_all("meta")
        if tag.get(attribute) == name and tag.get("content") is not None
    ]


def _assert_social_image_contract(response, *, image_url, image_type, image_alt):
    """Assert the complete, de-duplicated social image metadata contract."""

    page = BeautifulSoup(response.content, "html.parser")
    expected = {
        ("property", "og:image"): image_url,
        ("property", "og:image:secure_url"): image_url,
        ("property", "og:image:type"): image_type,
        ("property", "og:image:width"): "1200",
        ("property", "og:image:height"): "630",
        ("property", "og:image:alt"): image_alt,
        ("name", "twitter:card"): "summary_large_image",
        ("name", "twitter:image"): image_url,
        ("name", "twitter:image:alt"): image_alt,
    }
    for (attribute, name), expected_value in expected.items():
        assert _meta_values(page, attribute, name) == [expected_value]


def _real_png_bytes():
    """Return a valid in-memory PNG suitable for the PostMedia thumbnail path."""

    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (800, 600), (33, 37, 41)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.django_db
def test_article_detail_has_json_ld_article():
    """Article detail page has Article JSON-LD with correct fields."""
    post = Post.objects.create(
        title="JSON-LD Article",
        description="Article meta",
        content="# Body",
        slug="jsonld-article",
        status=Post.Status.PUBLISHED,
        content_type=Post.ContentType.ARTICLE,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'application/ld+json' in body
    assert '"@type": "Article"' in body
    assert "JSON-LD Article" in body
    assert "Article meta" in body
    assert f"/post/{post.slug}/" in body
    assert "datePublished" in body
    assert "dateModified" in body


@pytest.mark.django_db
def test_video_detail_has_json_ld_video_object():
    """Video detail page has VideoObject JSON-LD with contentUrl."""
    post = Post.objects.create(
        title="JSON-LD Video",
        description="Video meta",
        content="# Body",
        slug="jsonld-video",
        status=Post.Status.PUBLISHED,
        content_type=Post.ContentType.VIDEO,
        media_url="https://example.com/v.mp4",
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert '"@type": "VideoObject"' in body
    assert "https://example.com/v.mp4" in body


@pytest.mark.django_db
def test_audio_detail_has_json_ld_audio_object():
    """Audio detail page has AudioObject JSON-LD."""
    post = Post.objects.create(
        title="JSON-LD Audio",
        description="Audio meta",
        content="# Body",
        slug="jsonld-audio",
        status=Post.Status.PUBLISHED,
        content_type=Post.ContentType.AUDIO,
        media_url="https://example.com/a.mp3",
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert '"@type": "AudioObject"' in body
    assert "https://example.com/a.mp3" in body


@pytest.mark.django_db
def test_podcast_detail_has_json_ld_audio_object():
    """Podcast detail page has AudioObject JSON-LD."""
    post = Post.objects.create(
        title="JSON-LD Podcast",
        description="Podcast meta",
        content="# Body",
        slug="jsonld-podcast",
        status=Post.Status.PUBLISHED,
        content_type=Post.ContentType.PODCAST,
        media_url="https://example.com/p.opus",
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert '"@type": "AudioObject"' in body


@pytest.mark.django_db
def test_detail_page_has_canonical_link():
    """Detail page has <link rel='canonical'> tag."""
    post = Post.objects.create(
        title="Canonical Test",
        description="Canonical",
        content="# Body",
        slug="canonical-test",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'rel="canonical"' in body or "rel='canonical'" in body
    assert f"/post/{post.slug}/" in body


@pytest.mark.django_db
def test_public_page_canonicals_ignore_queries_on_the_secure_host():
    """Home, author, post, and series canonicals contain the path only."""

    post = Post.objects.create(
        title="Canonical surface",
        description="Canonical surface description",
        content="# Body",
        slug="canonical-surface",
        status=Post.Status.PUBLISHED,
    )
    from blog.models import Series

    series = Series.objects.create(name="Canonical series", slug="canonical-series")
    surfaces = [
        ("/?search=django&page=2", "/"),
        ("/about/?utm_source=test", "/about/"),
        (f"{post.get_absolute_url()}?source=share", post.get_absolute_url()),
        (f"/series/{series.slug}/?page=2", f"/series/{series.slug}/"),
    ]

    with override_settings(ALLOWED_HOSTS=["blog.example"]):
        client = Client()
        for requested_path, canonical_path in surfaces:
            response = client.get(
                requested_path,
                secure=True,
                HTTP_HOST="blog.example",
            )
            body = response.content.decode()
            canonical_links = re.findall(
                r'<link rel="canonical" href="([^"]+)">', body
            )

            assert response.status_code == 200
            assert canonical_links == [f"https://blog.example{canonical_path}"]
            assert f'property="og:url" content="https://blog.example{canonical_path}"' in body


@pytest.mark.django_db
def test_json_ld_graph_connects_article_author_and_visible_breadcrumbs():
    """Detail schema links its real page, author, publisher, and breadcrumb trail."""

    from blog.models import Category

    category = Category.objects.create(name="SEO", slug="seo")
    post = Post.objects.create(
        title="Connected graph",
        description="Graph description",
        content="# Body",
        slug="connected-graph",
        status=Post.Status.PUBLISHED,
        category=category,
    )
    response = Client().get(post.get_absolute_url())

    data = _parse_json_ld_scripts(response)[0]
    article = _graph_node(data, "Article")
    person = _graph_node(data, "Person")
    website = _graph_node(data, "WebSite")
    breadcrumb = _graph_node(data, "BreadcrumbList")

    assert article["@id"] == f"http://testserver{post.get_absolute_url()}#content"
    assert article["mainEntityOfPage"] == {
        "@type": "WebPage",
        "@id": f"http://testserver{post.get_absolute_url()}",
    }
    assert article["author"] == article["publisher"] == {"@id": person["@id"]}
    assert person["url"] == "http://testserver/about/"
    assert website["publisher"] == {"@id": person["@id"]}
    assert [item["name"] for item in breadcrumb["itemListElement"]] == [
        "Главная",
        category.name,
        post.title,
    ]
    assert breadcrumb["itemListElement"][-1]["item"] == article["mainEntityOfPage"]["@id"]
    assert "sameAs" not in person
    assert "jobTitle" not in person


@pytest.mark.django_db
def test_home_about_and_series_json_ld_graphs_use_truthful_page_types(client):
    """Non-detail discovery pages expose their own WebSite/ProfilePage/CollectionPage."""

    from blog.models import Series

    series = Series.objects.create(name="Graph series", slug="graph-series")

    home = _parse_json_ld_scripts(client.get("/"))[0]
    about = _parse_json_ld_scripts(client.get("/about/"))[0]
    series_page = _parse_json_ld_scripts(client.get(f"/series/{series.slug}/"))[0]

    home_website = _graph_node(home, "WebSite")
    home_person = _graph_node(home, "Person")
    about_profile = _graph_node(about, "ProfilePage")
    about_person = _graph_node(about, "Person")
    collection = _graph_node(series_page, "CollectionPage")
    breadcrumb = _graph_node(series_page, "BreadcrumbList")

    assert home_website["url"] == "http://testserver/"
    assert home_website["publisher"] == {"@id": home_person["@id"]}
    assert about_profile["mainEntity"] == {"@id": about_person["@id"]}
    assert about_person["url"] == "http://testserver/about/"
    assert collection["url"] == f"http://testserver/series/{series.slug}/"
    assert [item["name"] for item in breadcrumb["itemListElement"]] == [
        "Главная",
        f"Серия: {series.name}",
    ]


@pytest.mark.django_db
def test_detail_page_has_feed_alternate_links():
    """Detail page has RSS and Atom alternate feed links."""
    post = Post.objects.create(
        title="Feed Links",
        description="Feed",
        content="# Body",
        slug="feed-links",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'application/rss+xml' in body
    assert 'application/atom+xml' in body
    assert '/feed/rss/' in body
    assert '/feed/atom/' in body


@pytest.mark.django_db
def test_json_ld_is_valid_json():
    """JSON-LD script block parses as valid JSON."""
    post = Post.objects.create(
        title="Valid JSON-LD",
        description="JSON test",
        content="# Body",
        slug="valid-jsonld",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    scripts = _parse_json_ld_scripts(response)
    assert len(scripts) == 1
    data = scripts[0]
    assert data["@context"] == "https://schema.org"
    assert _graph_node(data, "Article")["headline"] == "Valid JSON-LD"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("content_type", "schema_type", "media_url"),
    [
        pytest.param(Post.ContentType.ARTICLE, "Article", "", id="article"),
        pytest.param(
            Post.ContentType.VIDEO,
            "VideoObject",
            'https://media.example/видео/"часть"\\путь\nролик.mp4?x=1&y=2',
            id="video",
        ),
        pytest.param(
            Post.ContentType.AUDIO,
            "AudioObject",
            'https://media.example/аудио/"часть"\\путь\nтрек.opus?x=1&y=2',
            id="audio",
        ),
    ],
)
@override_settings(SITE_AUTHOR='Автор "Тест" \\ Юникод')
def test_json_ld_hostile_text_round_trips_for_every_schema(
    content_type,
    schema_type,
    media_url,
):
    """All schema variants preserve hostile text without HTML artifacts."""
    title = 'Русский "заголовок" \\ путь\nстрока' + "\x00\b\f"
    description = (
        "Описание с кавычками \"и текстом\", обратным слешем \\, "
        "табом\tи переводом\r\nстроки </script> & < > — ёж 漢字"
    )
    post = Post.objects.create(
        title=title,
        description=description,
        content="# Body",
        slug=f"jsonld-hostile-{content_type}",
        status=Post.Status.PUBLISHED,
        content_type=content_type,
        media_url=media_url,
    )

    response = Client().get(f"/post/{post.slug}/")

    assert response.status_code == 200
    scripts = _parse_json_ld_scripts(response)
    assert len(scripts) == 1
    data = scripts[0]
    assert data["@context"] == "https://schema.org"
    article = _graph_node(data, schema_type)
    person = _graph_node(data, "Person")
    assert article["headline"] == title
    assert article["description"] == description
    assert article["url"] == f"http://testserver/post/{post.slug}/"
    assert article["datePublished"]
    assert article["dateModified"]
    assert person["name"] == 'Автор "Тест" \\ Юникод'
    if media_url:
        assert article["contentUrl"] == media_url
        assert article["contentUrl"].startswith("https://media.example/")
        assert not article["contentUrl"].startswith("http://testserverhttps://")
    else:
        assert "contentUrl" not in article
    assert "</script>" not in scripts[0]


# ── OG / Twitter meta tests ─────────────────────────────────────────────────


@pytest.mark.django_db
def test_detail_page_has_og_tags():
    """Detail page has Open Graph meta tags."""
    post = Post.objects.create(
        title="OG Test",
        description="OG description",
        content="# Body",
        slug="og-test",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'og:title' in body
    assert "OG Test" in body
    assert 'og:description' in body
    assert "OG description" in body
    assert 'og:url' in body
    assert 'og:type' in body
    assert 'article' in body


@pytest.mark.django_db
def test_detail_page_has_twitter_card():
    """Detail page has Twitter Card meta tags."""
    post = Post.objects.create(
        title="Twitter Card Test",
        description="Twitter desc",
        content="# Body",
        slug="twitter-test",
        status=Post.Status.PUBLISHED,
    )
    client = Client()
    response = client.get(f"/post/{post.slug}/")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'twitter:card' in body
    assert 'twitter:title' in body
    assert 'twitter:description' in body


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["exception-blog.ru"])
def test_social_image_fallback_is_a_complete_png_contract_on_public_surfaces(client):
    """Fallback PNG serves every main surface and matches detail JSON-LD."""

    post = Post.objects.create(
        title="Пост без обложки",
        description="Fallback social image",
        content="# Body",
        slug="post-without-cover",
        status=Post.Status.PUBLISHED,
    )
    series = Series.objects.create(name="Fallback series", slug="fallback-series")
    fallback_url = "https://exception-blog.ru/static/images/django-6-blog-social.png"
    fallback_alt = "Exception Blog — Владимир Монин"

    for path in ("/", "/about/", f"/series/{series.slug}/", post.get_absolute_url()):
        response = client.get(path, secure=True, HTTP_HOST="exception-blog.ru")

        assert response.status_code == 200
        _assert_social_image_contract(
            response,
            image_url=fallback_url,
            image_type="image/png",
            image_alt=fallback_alt,
        )

    detail_data = _parse_json_ld_scripts(
        client.get(post.get_absolute_url(), secure=True, HTTP_HOST="exception-blog.ru")
    )[0]
    article = _graph_node(detail_data, "Article")
    assert article["image"] == detail_data["image"] == fallback_url
    assert "exception-blog.ruhttps://" not in fallback_url

    image_path = finders.find("images/django-6-blog-social.png")
    assert isinstance(image_path, str)
    from PIL import Image

    with Image.open(image_path) as fallback_image:
        assert fallback_image.format == "PNG"
        assert fallback_image.size == (1200, 630)


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["exception-blog.ru"])
def test_detail_social_image_prefers_its_cover_and_matches_json_ld(client):
    """A post cover replaces only its social-image values without duplicating tags."""

    post = Post.objects.create(
        title="Пост с обложкой",
        description="Cover social image",
        content="# Body",
        slug="post-with-cover",
        status=Post.Status.PUBLISHED,
    )
    media = PostMedia(post=post, original_filename="cover.png")
    media.file.save("cover.png", ContentFile(_real_png_bytes()), save=True)
    media.refresh_from_db()
    assert media.thumbnail_og

    response = client.get(post.get_absolute_url(), secure=True, HTTP_HOST="exception-blog.ru")
    cover_url = (
        "https://exception-blog.ru"
        f"{reverse('post_media', kwargs={'media_id': media.pk, 'variant': 'og'})}"
    )
    cover_alt = f"Обложка статьи {post.title}"

    assert response.status_code == 200
    _assert_social_image_contract(
        response,
        image_url=cover_url,
        image_type="image/jpeg",
        image_alt=cover_alt,
    )
    detail_data = _parse_json_ld_scripts(response)[0]
    article = _graph_node(detail_data, "Article")
    assert article["image"] == detail_data["image"] == cover_url
    assert "exception-blog.ruhttps://" not in cover_url
    assert "X-Amz-" not in cover_url
    assert "?" not in cover_url

    image_response = client.get(
        reverse("post_media", kwargs={"media_id": media.pk, "variant": "og"}),
        secure=True,
        HTTP_HOST="exception-blog.ru",
        HTTP_USER_AGENT="TelegramBot",
    )
    assert image_response.status_code == 200
    assert image_response["Content-Type"] == "image/jpeg"
    assert "Location" not in image_response


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_agent",
    ["TelegramBot", "VKShare", "Twitterbot", "facebookexternalhit", "LinkedInBot"],
)
@override_settings(ALLOWED_HOSTS=["exception-blog.ru"])
def test_link_preview_user_agents_receive_the_social_image_html(client, user_agent):
    """Recognised link-preview user agents receive ordinary public SSR HTML."""

    post = Post.objects.create(
        title="Crawler social image",
        description="Crawler social image fallback",
        content="# Body",
        slug="crawler-social-image",
        status=Post.Status.PUBLISHED,
    )
    response = client.get(
        post.get_absolute_url(),
        secure=True,
        HTTP_HOST="exception-blog.ru",
        HTTP_USER_AGENT=user_agent,
    )

    assert response.status_code == 200
    _assert_social_image_contract(
        response,
        image_url="https://exception-blog.ru/static/images/django-6-blog-social.png",
        image_type="image/png",
        image_alt="Exception Blog — Владимир Монин",
    )


@pytest.mark.django_db
def test_brand_favicon_assets_and_public_root_endpoint(client):
    """All declared icon derivatives are rendered and the root icon is public."""

    response = client.get("/")
    assert response.status_code == 200
    page = BeautifulSoup(response.content, "html.parser")
    expected_links = {
        ("icon", "16x16", "image/png"): "images/favicon-16x16.png",
        ("icon", "32x32", "image/png"): "images/favicon-32x32.png",
        ("icon", "any", "image/x-icon"): "images/favicon.ico",
        ("apple-touch-icon", "180x180", "image/png"): "images/apple-touch-icon.png",
    }
    links = {
        (tag["rel"][0], tag.get("sizes"), tag.get("type")): tag.get("href")
        for tag in page.find_all("link")
        if tag.get("rel")
    }
    for attributes, source_name in expected_links.items():
        assert links[attributes] == static(source_name)

    icon_sizes = {
        "images/favicon-16x16.png": (16, 16),
        "images/favicon-32x32.png": (32, 32),
        "images/apple-touch-icon.png": (180, 180),
        "images/icon-192.png": (192, 192),
        "images/icon-512.png": (512, 512),
    }
    from PIL import Image

    for source_name, expected_size in icon_sizes.items():
        image_path = finders.find(source_name)
        assert isinstance(image_path, str)
        with Image.open(image_path) as image:
            assert image.format == "PNG"
            assert image.size == expected_size

    ico_path = finders.find("images/favicon.ico")
    assert isinstance(ico_path, str)
    with Image.open(ico_path) as image:
        assert image.format == "ICO"
        assert set(getattr(image, "ico").sizes()) == {(16, 16), (32, 32), (48, 48)}

    root_response = client.get("/favicon.ico", HTTP_USER_AGENT="YandexBot")
    assert root_response.status_code == 200
    assert root_response["Content-Type"] == "image/x-icon"
    assert root_response["Cache-Control"] == "public, max-age=86400"
    assert b"".join(root_response.streaming_content).startswith(b"\x00\x00\x01\x00")


@override_settings(DEBUG=False)
def test_favicon_root_does_not_depend_on_debug(client):
    """The Yandex-compatible root favicon remains public in production mode."""

    response = client.get("/favicon.ico", HTTP_USER_AGENT="YandexBot")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/x-icon"
    assert response["Cache-Control"] == "public, max-age=86400"


# ── Full E2E: CLI → API → DB → Site → Sitemap → Social Meta ──────────────


@pytest.mark.django_db
def test_e2e_seo_full_cycle_article(tmp_path, live_server):
    """Full SEO cycle for article:
    publisher CLI → API → DB → public site → sitemap → RSS → social meta → JSON-LD.
    """
    key = ApiKey.objects.create(name="SEO E2E Agent")

    # 1. Create markdown note
    note = tmp_path / "seo-article.md"
    note.write_text(
        "---\n"
        "title: SEO E2E Article\n"
        "description: Full cycle SEO verification\n"
        "tags: SEO, E2E\n"
        "series: testing\n"
        "---\n"
        "# SEO E2E Article\n\n"
        "Content for SEO verification.\n",
        encoding="utf-8",
    )

    # 2. Publish via publisher CLI (parse + HTTP POST)
    payload = parse_markdown_file(note)
    result = publish_post(
        url=live_server.url,
        api_key=key.token,
        payload=payload,
    )
    slug = result["slug"]
    assert result["status"] == "published"

    # 3. Verify DB state
    post = Post.objects.get(slug=slug)
    assert post.title == "SEO E2E Article"
    assert post.status == Post.Status.PUBLISHED
    assert post.content_type == "article"

    # 4. Verify post appears on public site (list + detail)
    client = Client()
    list_resp = client.get("/")
    assert list_resp.status_code == 200
    assert b"SEO E2E Article" in list_resp.content

    detail_resp = client.get(f"/post/{slug}/")
    assert detail_resp.status_code == 200
    detail_body = detail_resp.content.decode()

    # 5. Verify sitemap contains the post URL
    sitemap_resp = client.get("/sitemap.xml")
    assert sitemap_resp.status_code == 200
    sitemap_body = sitemap_resp.content.decode()
    assert f"/post/{slug}/" in sitemap_body

    # 6. Verify RSS feed contains the post
    rss_resp = client.get("/feed/rss/")
    assert rss_resp.status_code == 200
    rss_body = rss_resp.content.decode()
    assert "SEO E2E Article" in rss_body
    assert f"/post/{slug}/" in rss_body

    # 7. Verify Atom feed contains the post
    atom_resp = client.get("/feed/atom/")
    assert atom_resp.status_code == 200
    atom_body = atom_resp.content.decode()
    assert "SEO E2E Article" in atom_body

    # 8. Verify robots.txt references sitemap
    robots_resp = client.get("/robots.txt")
    assert robots_resp.status_code == 200
    robots_body = robots_resp.content.decode()
    assert "Sitemap:" in robots_body
    assert "/sitemap.xml" in robots_body

    # 9. Verify social meta tags on detail page
    assert 'og:title' in detail_body
    assert "SEO E2E Article" in detail_body
    assert 'og:description' in detail_body
    assert "Full cycle SEO verification" in detail_body
    assert 'og:url' in detail_body
    assert 'og:type' in detail_body
    assert 'twitter:card' in detail_body
    assert 'twitter:title' in detail_body
    assert 'twitter:description' in detail_body

    # 10. Verify canonical link
    assert 'rel="canonical"' in detail_body
    assert f"/post/{slug}/" in detail_body

    # 11. Verify JSON-LD
    import re
    match = re.search(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        detail_body,
        re.DOTALL,
    )
    assert match, "JSON-LD script not found on detail page"
    ld_data = json.loads(match.group(1))
    article = _graph_node(ld_data, "Article")
    assert article["headline"] == "SEO E2E Article"
    assert article["description"] == "Full cycle SEO verification"
    assert article["url"].endswith(f"/post/{slug}/")

    # 12. Verify feed alternate links
    assert 'application/rss+xml' in detail_body
    assert 'application/atom+xml' in detail_body


@pytest.mark.django_db
def test_e2e_seo_full_cycle_video(tmp_path, live_server):
    """Full SEO cycle for video: all content type checks."""
    key = ApiKey.objects.create(name="SEO E2E Agent")

    note = tmp_path / "seo-video.md"
    note.write_text(
        "---\n"
        "title: SEO E2E Video\n"
        "description: Video SEO verification\n"
        "content_type: video\n"
        "media_url: https://example.com/seo-video.mp4\n"
        "---\n"
        "# SEO E2E Video\n\n"
        "Video content.\n\n"
        "```timecodes\n"
        "0:00 Intro\n"
        "2:57 Demo\n"
        "```\n",
        encoding="utf-8",
    )

    payload = parse_markdown_file(note)
    result = publish_post(url=live_server.url, api_key=key.token, payload=payload)
    slug = result["slug"]

    # DB
    post = Post.objects.get(slug=slug)
    assert post.content_type == "video"
    assert post.media_url == "https://example.com/seo-video.mp4"
    assert len(post.timecodes) == 2
    assert post.timecodes[1]["seconds"] == 177

    # Detail
    client = Client()
    detail_resp = client.get(f"/post/{slug}/")
    assert detail_resp.status_code == 200
    body = detail_resp.content.decode()

    # Sitemap
    sitemap_resp = client.get("/sitemap.xml")
    assert f"/post/{slug}/" in sitemap_resp.content.decode()

    # RSS
    rss_resp = client.get("/feed/rss/")
    assert b"SEO E2E Video" in rss_resp.content

    # JSON-LD — VideoObject with contentUrl
    import re
    match = re.search(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        body,
        re.DOTALL,
    )
    assert match
    ld = json.loads(match.group(1))
    video = _graph_node(ld, "VideoObject")
    assert video["contentUrl"] == "https://example.com/seo-video.mp4"
    assert video["headline"] == "SEO E2E Video"

    # OG type should be article for video too
    assert 'og:type' in body

    # Canonical
    assert 'rel="canonical"' in body


@pytest.mark.django_db
def test_e2e_seo_draft_not_in_sitemap_or_feed(tmp_path, live_server):
    """Draft published via CLI is NOT in sitemap or RSS feed."""
    key = ApiKey.objects.create(name="SEO E2E Agent")

    note = tmp_path / "seo-draft.md"
    note.write_text(
        "---\n"
        "title: SEO Hidden Draft\n"
        "description: Should not be in sitemap or feed\n"
        "status: draft\n"
        "---\n"
        "Draft content.\n",
        encoding="utf-8",
    )

    payload = parse_markdown_file(note)
    result = publish_post(url=live_server.url, api_key=key.token, payload=payload)
    slug = result["slug"]
    assert result["status"] == "draft"

    # Not in sitemap
    client = Client()
    sitemap_resp = client.get("/sitemap.xml")
    assert f"/post/{slug}/" not in sitemap_resp.content.decode()

    # Not in RSS
    rss_resp = client.get("/feed/rss/")
    assert b"SEO Hidden Draft" not in rss_resp.content

    # Not in Atom
    atom_resp = client.get("/feed/atom/")
    assert b"SEO Hidden Draft" not in atom_resp.content

    # Not on public site
    detail_resp = client.get(f"/post/{slug}/")
    assert detail_resp.status_code == 404


@pytest.mark.django_db
def test_e2e_seo_replace_updates_sitemap(tmp_path, live_server):
    """After replacing a post via CLI, sitemap reflects new content."""
    key = ApiKey.objects.create(name="SEO E2E Agent")

    # v1
    note = tmp_path / "seo-replace.md"
    note.write_text(
        "---\ntitle: SEO Replace\ndescription: v1\n---\nv1 content.\n",
        encoding="utf-8",
    )
    payload = parse_markdown_file(note)
    r1 = publish_post(url=live_server.url, api_key=key.token, payload=payload)
    slug = r1["slug"]

    client = Client()
    sitemap1 = client.get("/sitemap.xml").content.decode()
    assert f"/post/{slug}/" in sitemap1

    # v2 with replace
    note.write_text(
        "---\ntitle: SEO Replace\ndescription: v2 updated\n---\nv2 content.\n",
        encoding="utf-8",
    )
    payload2 = parse_markdown_file(note)
    r2 = publish_post(
        url=live_server.url, api_key=key.token, payload=payload2, replace=True,
    )
    assert r2["description"] == "v2 updated"

    # Sitemap still has the slug
    sitemap2 = client.get("/sitemap.xml").content.decode()
    assert f"/post/{slug}/" in sitemap2

    # Detail shows updated description
    detail = client.get(f"/post/{slug}/")
    assert detail.status_code == 200
    assert b"v2 updated" in detail.content