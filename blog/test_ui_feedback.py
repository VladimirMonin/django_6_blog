from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from blog.models import Post
from blog.services import convert_markdown_to_html


pytestmark = pytest.mark.django_db
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_post(title="UI feedback post", content="Текст статьи"):
    return Post.objects.create(
        title=title,
        description="Короткое описание статьи",
        content=content,
        status=Post.Status.PUBLISHED,
    )


def soup(response):
    return BeautifulSoup(response.content, "html.parser")


def test_index_search_is_automatic_without_submit_button_and_uses_long_delay(client):
    create_post()

    response = client.get("/")

    page = soup(response)
    search_input = page.select_one("input.blog-search-input[name='search']")
    assert search_input is not None
    assert "delay:1500ms" in search_input["hx-trigger"]
    assert page.select_one("button.blog-search-button") is None


def test_detail_page_has_sticky_dynamic_breadcrumb_bar(client):
    post = create_post(content="## Первый раздел\n\nТекст\n\n### Внутри раздела\n\nЕщё текст")

    response = client.get(post.get_absolute_url())

    page = soup(response)
    sticky_nav = page.select_one("nav.breadcrumbs-dynamic[aria-label='Хлебные крошки']")
    assert sticky_nav is not None
    assert sticky_nav.select_one(".breadcrumbs-root a").get_text(strip=True) == "Главная"
    assert sticky_nav.select_one(".breadcrumbs-current").get_text(strip=True) == post.title


def test_footer_uses_2026_and_does_not_show_stack_listing(client):
    create_post()

    response = client.get("/")

    footer = soup(response).select_one("footer")
    footer_text = footer.get_text(" ", strip=True)
    assert "© 2026" in footer_text
    assert "© 2026 Владимир Монин" in footer.select_one(".footer-copyright").get_text(" ", strip=True)
    assert "SSR + HTMX + Bootstrap" not in footer_text
    assert "Построено на Django 6.0.5 с GPT-5.5" in footer_text
    assert "♥" in footer_text


def test_about_page_is_written_as_blog_page_not_stack_showcase(client):
    response = client.get("/about/")

    page_text = soup(response).get_text(" ", strip=True)
    assert "О блоге" in page_text
    assert "Владимир Монин" in page_text
    assert "живые заметки" in page_text.casefold()
    assert "Технологический стек" not in page_text
    assert "Концепция дизайна" not in page_text


def test_post_images_get_article_image_class_and_bounded_css():
    html = convert_markdown_to_html("![Большая схема](/media/posts/demo/huge.png)")
    css = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")

    page = BeautifulSoup(html, "html.parser")
    image = page.select_one("img.post-content-image")
    assert image is not None
    assert "img-fluid" in image.get("class", [])
    assert "max-height: min(72vh, 760px)" in css
    assert ".post-content img.post-content-image" in css


def test_mermaid_diagrams_have_svg_pan_zoom_assets_and_fullscreen_shell(client):
    post = create_post(content="```mermaid\ngraph TD\nA-->B\n```")

    response = client.get(post.get_absolute_url())

    page = soup(response)
    mermaid_shell = page.select_one(".mermaid-panzoom-shell .mermaid")
    assert mermaid_shell is not None
    body = response.content.decode()
    assert "svg-pan-zoom" in body
    js = (PROJECT_ROOT / "static/js/init-libs.js").read_text(encoding="utf-8")
    assert "startOnLoad: false" in js
    assert "svgPanZoom" in js
    assert "mermaid-panzoom-fullscreen" in js


def test_detail_meta_is_compact_row_with_author_first_and_dates_last(client):
    post = create_post()

    response = client.get(post.get_absolute_url())

    page = soup(response)
    meta = page.select_one(".post-detail-meta")
    assert meta is not None
    items = [item.get_text(" ", strip=True) for item in meta.select(".post-detail-meta-item")]
    assert items[0].startswith("Автор: Владимир Монин")
    assert "Создано:" not in meta.get_text(" ", strip=True)
    assert "Обновлено:" not in meta.get_text(" ", strip=True)


def test_post_card_shows_default_author(client):
    create_post()

    response = client.get("/")

    page = soup(response)
    author = page.select_one(".post-card-author")
    assert author is not None
    assert "Владимир Монин" in author.get_text(" ", strip=True)


def test_read_more_and_back_buttons_hide_text_on_mobile_but_keep_accessible_label(client):
    post = create_post()

    index_page = soup(client.get("/"))
    read_more = index_page.select_one("a[aria-label='Читать далее']")
    assert read_more is not None
    assert read_more.select_one("i.bi-arrow-right") is not None
    assert "d-none" in read_more.select_one(".button-text").get("class", [])
    assert "d-sm-inline" in read_more.select_one(".button-text").get("class", [])

    detail_page = soup(client.get(post.get_absolute_url()))
    back = detail_page.select_one("a[aria-label='Назад к списку']")
    assert back is not None
    children = [child for child in back.children if getattr(child, "name", None)]
    assert children[0].name == "i"
    assert "bi-arrow-left" in children[0].get("class", [])
    assert "d-none" in back.select_one(".button-text").get("class", [])
    assert "d-sm-inline" in back.select_one(".button-text").get("class", [])


@pytest.mark.parametrize(
    ("callout_type", "icon_class"),
    [
        ("info", "bi-info-circle-fill"),
        ("warning", "bi-exclamation-triangle-fill"),
        ("success", "bi-check-circle-fill"),
        ("error", "bi-x-octagon-fill"),
        ("danger", "bi-x-octagon-fill"),
        ("tip", "bi-lightbulb-fill"),
        ("note", "bi-sticky-fill"),
        ("important", "bi-exclamation-circle-fill"),
        ("summary", "bi-list-check"),
    ],
)
def test_obsidian_callouts_render_bootstrap_icons_per_type(callout_type, icon_class):
    page = BeautifulSoup(
        convert_markdown_to_html(
            f"> [!{callout_type}] Заголовок\n"
            "> Текст выноски"
        ),
        "html.parser",
    )

    callout = page.select_one(f"blockquote.callout-{callout_type}")
    assert callout is not None
    assert callout.select_one(f"i.{icon_class}.callout-icon") is not None
