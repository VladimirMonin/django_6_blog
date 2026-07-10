import shutil
import subprocess
import textwrap
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.db import connection
from django.test.utils import CaptureQueriesContext

from blog.models import Category, Post, PostMedia, Tag
from blog.services import convert_markdown_to_html

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = PROJECT_ROOT / "test-artifacts" / "element-screenshots"
CSS_FILES = [
    PROJECT_ROOT / "static" / "css" / "style.css",
    PROJECT_ROOT / "blog" / "components" / "post_card" / "post_card.css",
    PROJECT_ROOT / "blog" / "components" / "paginator" / "paginator.css",
    PROJECT_ROOT / "blog" / "components" / "button" / "button.css",
    PROJECT_ROOT / "blog" / "components" / "alert" / "alert.css",
]

pytestmark = pytest.mark.django_db


def create_post(
    title,
    content="Текст публикации",
    *,
    category=None,
    tags=(),
    content_type=Post.ContentType.ARTICLE,
):
    post = Post.objects.create(
        title=title,
        content=content,
        status=Post.Status.PUBLISHED,
        category=category,
        content_type=content_type,
    )
    if tags:
        post.tags.set(tags)
    return post


def soup(response):
    return BeautifulSoup(response.content, "html.parser")


def test_markdown_renderer_outputs_expected_article_html_without_raw_obsidian_markers():
    html = convert_markdown_to_html(
        textwrap.dedent(
            """
            # Заголовок

            > [!important]
            > Важная мысль

            | Колонка | Значение |
            | --- | --- |
            | Django | 6 |

            ```python
            print("ok")
            ```

            ```mermaid
            graph TD
              A-->B
            ```

            - [x] готово
            """
        )
    )
    page = BeautifulSoup(html, "html.parser")

    assert page.select_one("h1").get_text(strip=True) == "Заголовок"
    assert page.select_one("blockquote.alert") is not None
    assert "[!important]" not in html
    assert page.select_one("table.table") is not None
    assert page.select_one("code.language-python") is not None
    assert page.select_one(".mermaid") is not None
    assert "graph TD" in page.select_one(".mermaid").get_text()
    assert page.select_one("input[type='checkbox'][checked]") is not None


def test_post_card_excerpt_strips_markdown_table_syntax():
    post = Post(
        title="Карточка",
        content=textwrap.dedent(
            """
            # Карточка

            Текст с **Markdown** и таблицей.

            | A | B |
            |---|---|
            | 1 | 2 |
            """
        ),
    )

    excerpt = post.plain_text_excerpt

    assert "Текст с Markdown и таблицей" in excerpt
    assert "|" not in excerpt
    assert "---" not in excerpt


def test_full_and_htmx_index_use_expected_templates_and_partial_boundaries(client):
    category = Category.objects.create(name="Django", slug="django")
    for index in range(7):
        create_post(
            f"Django HTMX {index}",
            category=category,
            content_type=Post.ContentType.VIDEO,
        )

    filters = {"search": "Django", "type": Post.ContentType.VIDEO}
    full_response = client.get("/", filters)
    htmx_response = client.get("/", filters, HTTP_HX_REQUEST="true")
    load_more_response = client.get(
        "/",
        {**filters, "page": "2", "load_more": "true"},
        HTTP_HX_REQUEST="true",
    )

    assert full_response.status_code == 200
    assert [template.name for template in full_response.templates if template.name][0] == "blog/post_list.html"
    assert soup(full_response).select_one("html") is not None

    assert htmx_response.status_code == 200
    assert [template.name for template in htmx_response.templates if template.name][0] == "blog/_post_list_partial.html"
    htmx_page = soup(htmx_response)
    assert htmx_page.select_one("html") is None
    htmx_paginator = htmx_page.select_one("#paginator-nav[hx-swap-oob='true']")
    assert htmx_paginator is not None
    for navigation in htmx_paginator.select("a[href], button[hx-get]"):
        url = navigation.get("href") or navigation["hx-get"]
        assert parse_qs(urlparse(url).query)["type"] == [Post.ContentType.VIDEO]

    assert load_more_response.status_code == 200
    assert [template.name for template in load_more_response.templates if template.name][0] == "blog/_post_cards_only.html"
    load_more_page = soup(load_more_response)
    assert load_more_page.select_one("html") is None
    load_more_paginator = load_more_page.select_one("#paginator-nav[hx-swap-oob='true']")
    assert load_more_paginator is not None
    for navigation in load_more_paginator.select("a[href], button[hx-get]"):
        url = navigation.get("href") or navigation["hx-get"]
        assert parse_qs(urlparse(url).query)["type"] == [Post.ContentType.VIDEO]
    assert len(load_more_page.select(".post-card")) == 2


def test_htmx_load_more_button_targets_stable_container_and_preserves_filters(client):
    category = Category.objects.create(name="Оптимизация", slug="optimization")
    tag = Tag.objects.create(name="HTMX", slug="htmx")
    for index in range(7):
        create_post(f"HTMX карточка {index}", category=category, tags=[tag])

    response = client.get("/", {"search": "карточка", "category": category.slug, "tag": tag.slug})

    assert response.status_code == 200
    page = soup(response)
    post_container = page.select_one("#post-container")
    load_more = page.select_one("button[hx-get*='load_more=true']")

    assert post_container is not None
    assert load_more is not None
    assert load_more["hx-target"] == "#post-container"
    assert load_more["hx-swap"] == "beforeend"

    params = parse_qs(urlparse(load_more["hx-get"]).query)
    assert params["search"] == ["карточка"]
    assert params["category"] == [category.slug]
    assert params["tag"] == [tag.slug]
    assert params["load_more"] == ["true"]


def query_count_for_homepage(client, number_of_posts):
    category = Category.objects.create(name=f"Категория {number_of_posts}")
    tag = Tag.objects.create(name=f"Тег {number_of_posts}")
    for index in range(number_of_posts):
        post = create_post(f"Пост {number_of_posts}-{index}", category=category, tags=[tag])
        media = PostMedia(post=post, original_filename=f"cover-{number_of_posts}-{index}.webp")
        media.file.save(f"cover-{number_of_posts}-{index}.webp", ContentFile(b"RIFFxxxxWEBP"), save=True)

    with CaptureQueriesContext(connection) as captured:
        response = client.get("/")

    assert response.status_code == 200
    return len(captured)


def test_homepage_query_count_is_stable_for_post_cards_with_categories_tags_and_media(client):
    one_post_queries = query_count_for_homepage(client, 1)
    Post.objects.all().delete()
    Category.objects.all().delete()
    Tag.objects.all().delete()

    seven_post_queries = query_count_for_homepage(client, 7)

    assert seven_post_queries <= one_post_queries + 1
    assert seven_post_queries <= 8


def reset_snapshot_dir():
    shutil.rmtree(SNAPSHOT_DIR, ignore_errors=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def inline_css():
    css = []
    for css_file in CSS_FILES:
        if css_file.exists():
            css.append(css_file.read_text(encoding="utf-8"))
    css.append(
        """
        body { margin: 0; padding: 24px; background: #f3f4f6; font-family: system-ui, sans-serif; }
        .snapshot-frame { max-width: 920px; margin: 0 auto; }
        .row { display: block; }
        .col { max-width: 520px; }
        .card { background: white; border: 1px solid #e5e7eb; border-radius: 16px; overflow: hidden; }
        .card-body { padding: 20px; }
        .badge { display: inline-block; padding: 0.35rem 0.6rem; border-radius: 999px; background: #f8fafc; }
        .btn { display: inline-block; padding: 0.55rem 0.85rem; border-radius: 10px; background: #111827; color: white; text-decoration: none; }
        .pagination { display: flex; gap: 8px; list-style: none; padding: 0; }
        .page-link { display: block; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 10px; background: white; }
        """
    )
    return "\n".join(css)


def write_element_html(source_html, selector, name):
    page = BeautifulSoup(source_html, "html.parser")
    element = page.select_one(selector)
    assert element is not None, f"selector {selector!r} was not found"
    html_file = SNAPSHOT_DIR / f"{name}.html"
    html_file.write_text(
        "\n".join(
            [
                "<!doctype html>",
                '<html lang="ru">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                f"<style>{inline_css()}</style>",
                "</head>",
                "<body>",
                '<main class="snapshot-frame">',
                str(element),
                "</main>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )
    return html_file


def take_firefox_screenshot(html_file, name):
    firefox = shutil.which("firefox")
    if not firefox:
        pytest.skip("firefox is not installed; visual element snapshots are skipped")

    output = SNAPSHOT_DIR / f"{name}.png"
    profile_dir = SNAPSHOT_DIR / f"{name}-firefox-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            firefox,
            "--headless",
            "--new-instance",
            "--profile",
            str(profile_dir),
            "--window-size",
            "920,720",
            "--screenshot",
            str(output),
            html_file.resolve().as_uri(),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert output.exists(), result.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output.stat().st_size > 2_000
    shutil.rmtree(profile_dir, ignore_errors=True)
    html_file.unlink(missing_ok=True)
    return output


def test_visual_element_screenshots_are_generated_from_rendered_templates_without_accumulating(client):
    stale_file = SNAPSHOT_DIR / "stale.png"
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stale_file.write_bytes(b"old")

    reset_snapshot_dir()
    assert not stale_file.exists()

    category = Category.objects.create(name="LM Studio", slug="lm-studio")
    tag = Tag.objects.create(name="Django", slug="django")
    for index in range(7):
        create_post(
            f"Карточка {index}",
            content="# Карточка\n\nТекст с **Markdown** и таблицей.\n\n| A | B |\n|---|---|\n| 1 | 2 |",
            category=category,
            tags=[tag],
        )

    index_response = client.get("/")
    detail_response = client.get(Post.objects.order_by("-created_at").first().get_absolute_url())
    assert index_response.status_code == 200
    assert detail_response.status_code == 200

    snapshots = {
        "blog-hero": write_element_html(index_response.content, ".blog-hero", "blog-hero"),
        "post-card": write_element_html(index_response.content, ".post-card", "post-card"),
        "paginator": write_element_html(index_response.content, "#paginator-nav", "paginator"),
        "post-reactions": write_element_html(detail_response.content, ".post-reactions", "post-reactions"),
        "markdown-content": write_element_html(detail_response.content, ".markdown-content", "markdown-content"),
    }

    generated = [take_firefox_screenshot(html_file, name) for name, html_file in snapshots.items()]

    assert sorted(path.name for path in generated) == [
        "blog-hero.png",
        "markdown-content.png",
        "paginator.png",
        "post-card.png",
        "post-reactions.png",
    ]
    assert not list(SNAPSHOT_DIR.glob("*.html"))
