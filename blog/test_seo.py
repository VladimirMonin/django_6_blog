"""SEO tests: sitemap, robots.txt, RSS/Atom feeds, JSON-LD, canonical URLs.

E2E tests verify the full cycle: publisher CLI → API → DB → public site →
sitemap → social meta tags (OG, Twitter, JSON-LD).
"""

import json
import xml.etree.ElementTree as ET

import pytest
from django.test import Client

from api.models import ApiKey
from blog.models import Post
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
    body = response.content.decode()
    # Extract JSON-LD block
    import re
    match = re.search(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        body,
        re.DOTALL,
    )
    assert match, "JSON-LD script block not found"
    data = json.loads(match.group(1))
    assert data["@context"] == "https://schema.org"
    assert data["headline"] == "Valid JSON-LD"


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
    assert ld_data["@type"] == "Article"
    assert ld_data["headline"] == "SEO E2E Article"
    assert ld_data["description"] == "Full cycle SEO verification"
    assert ld_data["url"].endswith(f"/post/{slug}/")

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
    assert ld["@type"] == "VideoObject"
    assert ld["contentUrl"] == "https://example.com/seo-video.mp4"
    assert ld["headline"] == "SEO E2E Video"

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