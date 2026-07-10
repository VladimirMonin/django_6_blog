"""Tests for navigation features: related posts, breadcrumbs, TOC, series landing."""

import pytest
from django.test import Client
from django.urls import reverse

from blog.models import Category, Post, Series, Tag


def create_post(
    title,
    *,
    content="Текст",
    description="Описание",
    status=Post.Status.PUBLISHED,
    category=None,
    tags=(),
    series=None,
    series_order=0,
):
    post = Post.objects.create(
        title=title,
        content=content,
        description=description,
        status=status,
        category=category,
        series=series,
        series_order=series_order,
    )
    if tags:
        post.tags.set(tags)
    return post


# --- Related posts ---------------------------------------------------------


@pytest.mark.django_db
def test_related_posts_same_category_three_appear(client):
    """4 posts in same category: viewing one shows 3 related (not itself)."""
    cat = Category.objects.create(name="Django", slug="django")
    p1 = create_post("Post 1", category=cat)
    p2 = create_post("Post 2", category=cat)
    p3 = create_post("Post 3", category=cat)
    p4 = create_post("Post 4", category=cat)

    response = client.get(p1.get_absolute_url())
    assert response.status_code == 200
    body = response.content.decode()

    # The other 3 should appear in related section
    assert "Post 2" in body
    assert "Post 3" in body
    assert "Post 4" in body
    # Current post title should not appear as a related link
    # (it appears in the main <h1> and breadcrumbs, but not in related section)
    assert "Похожие записи" in body


@pytest.mark.django_db
def test_related_posts_excludes_current(client):
    """Related posts must not include the current post."""
    cat = Category.objects.create(name="Python", slug="python")
    current = create_post("Current Post", category=cat)
    other = create_post("Other Post", category=cat)

    response = client.get(current.get_absolute_url())
    assert response.status_code == 200
    context = response.context
    related = context["related_posts"]
    related_titles = [p.title for p in related]
    assert "Current Post" not in related_titles
    assert "Other Post" in related_titles


@pytest.mark.django_db
def test_related_posts_shared_tags(client):
    """Posts with shared tags appear in related posts."""
    tag_django = Tag.objects.create(name="Django", slug="django")
    tag_py = Tag.objects.create(name="Python", slug="python")

    current = create_post("Tagged Post A", tags=[tag_django, tag_py])
    related1 = create_post("Tagged Post B", tags=[tag_django])
    related2 = create_post("Tagged Post C", tags=[tag_py])
    unrelated = create_post("Unrelated Post")

    response = client.get(current.get_absolute_url())
    assert response.status_code == 200
    context = response.context
    related = context["related_posts"]
    related_titles = {p.title for p in related}
    assert "Tagged Post B" in related_titles
    assert "Tagged Post C" in related_titles
    assert "Unrelated Post" not in related_titles


@pytest.mark.django_db
def test_related_posts_excludes_drafts_and_deleted(client):
    """Related posts must only include published, non-deleted posts."""
    cat = Category.objects.create(name="Web", slug="web")
    current = create_post("Main Post", category=cat)
    create_post("Published Related", category=cat)
    create_post("Draft Related", category=cat, status=Post.Status.DRAFT)
    deleted = create_post("Deleted Related", category=cat)
    deleted.deleted_at = deleted.created_at
    deleted.save(update_fields=["deleted_at"])

    response = client.get(current.get_absolute_url())
    assert response.status_code == 200
    related_titles = [p.title for p in response.context["related_posts"]]
    assert "Published Related" in related_titles
    assert "Draft Related" not in related_titles
    assert "Deleted Related" not in related_titles


# --- Breadcrumbs -----------------------------------------------------------


@pytest.mark.django_db
def test_breadcrumbs_detail_page_has_links(client):
    """Detail page should render breadcrumb links from context."""
    cat = Category.objects.create(name="Tutorial", slug="tutorial")
    post = create_post("Breadcrumbs Post", category=cat)

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200

    breadcrumbs = response.context["breadcrumbs"]
    assert len(breadcrumbs) >= 2
    assert breadcrumbs[0]["title"] == "Главная"
    assert breadcrumbs[0]["url"] == "/"
    # Category in the middle
    assert any(b["title"] == "Tutorial" for b in breadcrumbs)
    # Last is the post title (no url = current page)
    assert breadcrumbs[-1]["title"] == "Breadcrumbs Post"
    assert "url" not in breadcrumbs[-1]

    body = response.content.decode()
    assert "breadcrumb" in body.lower()
    assert "Главная" in body
    assert "Tutorial" in body
    assert 'aria-label="Хлебные крошки"' in body
    assert body.count('class="breadcrumbs-dynamic article-breadcrumbs-sticky"') == 1


@pytest.mark.django_db
def test_breadcrumbs_without_category(client):
    """Post without category still has Home > Title breadcrumbs."""
    post = create_post("No Category Post")

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200
    breadcrumbs = response.context["breadcrumbs"]
    assert len(breadcrumbs) == 2
    assert breadcrumbs[0]["title"] == "Главная"
    assert breadcrumbs[-1]["title"] == "No Category Post"


# --- Table of Contents -----------------------------------------------------


@pytest.mark.django_db
def test_toc_with_four_h2_headings(client):
    """Post with 4 h2 headings should have a TOC with 4 entries."""
    content = (
        "# Intro\n\n"
        "## Heading One\n\nText.\n\n"
        "## Heading Two\n\nText.\n\n"
        "## Heading Three\n\nText.\n\n"
        "## Heading Four\n\nText.\n"
    )
    post = create_post("TOC Post", content=content)

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200
    toc = response.context["toc"]
    assert len(toc) == 4
    texts = [entry["text"] for entry in toc]
    assert "Heading One" in texts
    assert "Heading Four" in texts
    for entry in toc:
        assert entry["level"] == 2
        assert entry["id"]

    body = response.content.decode()
    assert "Содержание" in body
    assert 'id="post-toc-collapse"' in body
    assert 'class="collapse show" id="post-toc-collapse"' not in body
    assert 'aria-expanded="false"' in body
    for entry in toc:
        href = f'href="#{entry["id"]}"'
        target = f'id="{entry["id"]}"'
        assert href in body
        assert target in body


@pytest.mark.django_db
def test_toc_cyrillic_headings_have_real_body_anchors(client):
    """Cyrillic TOC links should point to actual h2/h3 ids, not empty # anchors."""
    content = (
        "# Заголовок\n\n"
        "## Первый раздел\n\nТекст.\n\n"
        "## Второй раздел\n\nТекст.\n\n"
        "### Важная деталь\n\nТекст.\n\n"
        "## Третий раздел\n\nТекст.\n"
    )
    post = create_post("Кириллический TOC", content=content)

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200
    toc = response.context["toc"]
    body_html = response.context["body_html"]

    assert len(toc) == 4
    assert all(entry["id"] for entry in toc)
    assert [entry["id"] for entry in toc] == [
        "post-section-1",
        "post-section-2",
        "post-section-3",
        "post-section-4",
    ]
    for entry in toc:
        assert f'href="#{entry["id"]}"' in response.content.decode()
        assert f'id="{entry["id"]}"' in body_html


@pytest.mark.django_db
def test_toc_with_one_heading_not_shown(client):
    """Post with 1 heading should not have a TOC."""
    content = "# Title\n\n## Only One\n\nText.\n"
    post = create_post("Single Heading Post", content=content)

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200
    toc = response.context["toc"]
    assert len(toc) == 0
    body = response.content.decode()
    assert "Содержание" not in body


# --- Series landing page ---------------------------------------------------


@pytest.mark.django_db
def test_series_landing_shows_all_posts_in_order(client):
    """/series/<slug>/ shows all posts in series ordered by series_order."""
    series = Series.objects.create(name="Django Course", slug="django-course")
    p1 = create_post("Lesson 1", series=series, series_order=1)
    p2 = create_post("Lesson 2", series=series, series_order=2)
    p3 = create_post("Lesson 3", series=series, series_order=3)

    url = reverse("series_detail", kwargs={"slug": series.slug})
    response = client.get(url)
    assert response.status_code == 200
    body = response.content.decode()

    assert "Django Course" in body
    assert "Lesson 1" in body
    assert "Lesson 2" in body
    assert "Lesson 3" in body

    # Verify ordering in context
    posts = list(response.context["series_posts"])
    assert [p.title for p in posts] == ["Lesson 1", "Lesson 2", "Lesson 3"]


@pytest.mark.django_db
def test_series_landing_excludes_other_series(client):
    """Posts from other series don't appear on a series landing page."""
    series_a = Series.objects.create(name="Series A", slug="series-a")
    series_b = Series.objects.create(name="Series B", slug="series-b")
    create_post("A Post 1", series=series_a, series_order=1)
    create_post("A Post 2", series=series_a, series_order=2)
    create_post("B Post 1", series=series_b, series_order=1)

    url = reverse("series_detail", kwargs={"slug": series_a.slug})
    response = client.get(url)
    assert response.status_code == 200
    body = response.content.decode()

    assert "A Post 1" in body
    assert "A Post 2" in body
    assert "B Post 1" not in body


@pytest.mark.django_db
def test_series_landing_excludes_drafts_and_deleted(client):
    """Series landing only shows published, non-deleted posts."""
    series = Series.objects.create(name="Filtered Series", slug="filtered-series")
    create_post("Published", series=series, series_order=1)
    create_post("Draft", series=series, series_order=2, status=Post.Status.DRAFT)
    deleted = create_post("Deleted", series=series, series_order=3)
    deleted.deleted_at = deleted.created_at
    deleted.save(update_fields=["deleted_at"])

    url = reverse("series_detail", kwargs={"slug": series.slug})
    response = client.get(url)
    assert response.status_code == 200
    posts = list(response.context["series_posts"])
    titles = [p.title for p in posts]
    assert "Published" in titles
    assert "Draft" not in titles
    assert "Deleted" not in titles


@pytest.mark.django_db
def test_series_landing_404_for_unknown_slug(client):
    """Unknown series slug returns 404."""
    url = reverse("series_detail", kwargs={"slug": "nonexistent-series"})
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_series_navigation_excludes_soft_deleted_members(client):
    series = Series.objects.create(name="Clean Navigation", slug="clean-navigation")
    previous = create_post("Visible Previous", series=series, series_order=1)
    deleted_before = create_post("Deleted Before", series=series, series_order=2)
    current = create_post("Current Lesson", series=series, series_order=3)
    deleted_after = create_post("Deleted After", series=series, series_order=4)
    following = create_post("Visible Next", series=series, series_order=5)
    for deleted in (deleted_before, deleted_after):
        deleted.deleted_at = deleted.created_at
        deleted.save(update_fields=["deleted_at"])

    response = client.get(current.get_absolute_url())

    assert response.status_code == 200
    assert response.context["series_prev"] == {
        "slug": previous.slug,
        "title": previous.title,
    }
    assert response.context["series_next"] == {
        "slug": following.slug,
        "title": following.title,
    }
    assert response.context["series_position"] == 2
    assert response.context["series_total"] == 3


# --- Soft delete guard -----------------------------------------------------


@pytest.mark.django_db
def test_related_posts_filter_deleted_at_isnull(client):
    """Related posts queryset must filter deleted_at__isnull=True."""
    cat = Category.objects.create(name="Guard", slug="guard")
    current = create_post("Guard Current", category=cat)
    create_post("Guard Related", category=cat)

    response = client.get(current.get_absolute_url())
    assert response.status_code == 200
    for post in response.context["related_posts"]:
        assert post.deleted_at is None


@pytest.mark.django_db
def test_series_landing_filter_deleted_at_isnull(client):
    """Series landing queryset must filter deleted_at__isnull=True."""
    series = Series.objects.create(name="Guard Series", slug="guard-series")
    create_post("Guard Series Post", series=series, series_order=1)

    url = reverse("series_detail", kwargs={"slug": series.slug})
    response = client.get(url)
    assert response.status_code == 200
    for post in response.context["series_posts"]:
        assert post.deleted_at is None