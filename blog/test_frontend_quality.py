"""Tests for frontend quality: accessibility, lazy-load, mobile typography."""
import pytest
from django.test import Client
from blog.models import Post, Category


@pytest.fixture
def published_post():
    cat = Category.objects.create(name="Tech", slug="tech")
    post = Post.objects.create(
        title="Frontend Quality Test",
        description="Testing accessibility and lazy load",
        content="# Heading\n\n## Section A\n\nSome text.\n\n## Section B\n\nMore text.\n\n![Image](https://example.com/img.png)",
        slug="frontend-quality-test",
        status=Post.Status.PUBLISHED,
        category=cat,
    )
    return post


@pytest.mark.django_db
def test_detail_page_has_skip_link(published_post):
    """Detail page must have a skip link for keyboard users."""
    response = Client().get(f"/post/{published_post.slug}/")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'skip-link' in html
    assert '#main-content' in html


@pytest.mark.django_db
def test_detail_page_has_main_content_id(published_post):
    """Main content must have id='main-content' as skip link target."""
    response = Client().get(f"/post/{published_post.slug}/")
    html = response.content.decode()
    assert 'id="main-content"' in html


@pytest.mark.django_db
def test_lazy_load_script_is_present(published_post):
    """Lazy-load JS script must be in the page."""
    response = Client().get(f"/post/{published_post.slug}/")
    html = response.content.decode()
    assert 'lazy-load-images.js' in html


@pytest.mark.django_db
def test_list_page_has_skip_link():
    """List page must also have skip link."""
    response = Client().get("/")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'skip-link' in html


@pytest.mark.django_db
def test_detail_page_has_breadcrumbs(published_post):
    """Detail page must have breadcrumb navigation."""
    response = Client().get(f"/post/{published_post.slug}/")
    html = response.content.decode()
    assert 'breadcrumb' in html.lower()
    assert 'Главная' in html


@pytest.mark.django_db
def test_css_contains_accessibility_styles():
    """CSS file must contain accessibility-related styles."""
    import os
    from django.conf import settings
    css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
    with open(css_path, 'r') as f:
        css = f.read()
    assert 'skip-link' in css
    assert 'focus-visible' in css
    assert 'skeleton-pulse' in css


@pytest.mark.django_db
def test_css_contains_mobile_typography():
    """CSS must have mobile-specific typography rules."""
    import os
    from django.conf import settings
    css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
    with open(css_path, 'r') as f:
        css = f.read()
    assert 'max-width: 576px' in css
    assert '.post-content' in css
    assert 'line-height' in css


@pytest.mark.django_db
def test_css_contains_related_posts_styles():
    """CSS must have related-posts styling."""
    import os
    from django.conf import settings
    css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
    with open(css_path, 'r') as f:
        css = f.read()
    assert '.related-posts' in css
    assert '.related-post-card' in css


@pytest.mark.django_db
def test_css_contains_toc_styles():
    """CSS must have TOC card styling."""
    import os
    from django.conf import settings
    css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
    with open(css_path, 'r') as f:
        css = f.read()
    assert '.toc-card' in css


@pytest.mark.django_db
def test_css_contains_series_landing_styles():
    """CSS must have series landing page styling."""
    import os
    from django.conf import settings
    css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
    with open(css_path, 'r') as f:
        css = f.read()
    assert '.series-detail-header' in css
    assert '.series-post-item' in css