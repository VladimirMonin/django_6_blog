"""Tests for frontend quality: accessibility, lazy-load, mobile typography."""

import pytest
from bs4 import BeautifulSoup
from django.test import Client

from blog.models import Category, Post, Series


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
def test_navbar_toggler_exposes_accessible_collapse_contract():
    response = Client().get("/")
    page = BeautifulSoup(response.content, "html.parser")

    toggler = page.select_one("button.navbar-toggler")
    assert toggler is not None
    assert toggler["aria-label"] == "Переключить навигацию"
    assert toggler["aria-expanded"] == "false"
    collapse_id = toggler["aria-controls"]
    collapse = page.find(id=collapse_id)
    assert collapse_id == "navbarNav"
    assert toggler["data-bs-target"] == f"#{collapse_id}"
    assert collapse is not None
    assert {"collapse", "navbar-collapse"}.issubset(collapse.get("class", []))
    assert toggler.select_one(".navbar-toggler-icon")["aria-hidden"] == "true"
    assert all(
        icon.get("aria-hidden") == "true"
        for icon in page.select("nav.navbar i.bi")
    )


@pytest.mark.django_db
def test_series_page_has_one_current_breadcrumb_navigation():
    series = Series.objects.create(name="Доступная серия", slug="accessible-series")

    response = Client().get(f"/series/{series.slug}/")
    page = BeautifulSoup(response.content, "html.parser")

    breadcrumbs = page.select('nav[aria-label="Хлебные крошки"]')
    assert len(breadcrumbs) == 1
    breadcrumb_list = breadcrumbs[0].select_one("ol.breadcrumb")
    assert breadcrumb_list is not None
    items = breadcrumb_list.find_all("li", recursive=False)
    assert len(items) == 2
    assert items[0].select_one('a[href="/"]').get_text(strip=True) == "Главная"
    current = breadcrumb_list.select('[aria-current="page"]')
    assert len(current) == 1
    assert current[0].get_text(" ", strip=True) == "Серия: Доступная серия"
    assert current[0].name == "li"
    assert current[0]["aria-current"] == "page"


@pytest.mark.django_db
def test_current_paginator_page_and_icons_have_accessible_semantics():
    for index in range(6):
        Post.objects.create(
            title=f"Страница {index}",
            description="Проверка пагинации",
            content="Текст",
            slug=f"accessibility-page-{index}",
            status=Post.Status.PUBLISHED,
        )

    response = Client().get("/?page=2")
    page = BeautifulSoup(response.content, "html.parser")
    paginator = page.select_one("#paginator-nav")

    assert paginator is not None
    current_elements = paginator.select('[aria-current="page"]')
    assert len(current_elements) == 1
    current_link = current_elements[0]
    assert current_link.name == "a"
    assert current_link.get_text(strip=True) == "2"
    assert "active" in current_link.parent.get("class", [])

    page_links = paginator.select("a.page-link")
    assert all(
        link.get("aria-current") is None
        for link in page_links
        if link is not current_link
    )
    assert paginator.select_one('a.page-link[href*="page=1"]:not([aria-current])')
    assert all(icon.get("aria-hidden") == "true" for icon in paginator.select("i.bi"))


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