from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from blog.models import Category, Post
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
    read_more_children = read_more.find_all(recursive=False)
    assert read_more_children[0].name == "span"
    assert read_more_children[1].name == "i"
    assert "bi-arrow-right" in str(read_more_children[1].get("class"))
    assert "button-icon-end" in str(read_more_children[1].get("class"))
    assert "d-none" in read_more.select_one(".button-text").get("class", [])
    assert "d-sm-inline" in read_more.select_one(".button-text").get("class", [])

    detail_page = soup(client.get(post.get_absolute_url()))
    back = detail_page.select_one("a[aria-label='Назад к списку']")
    assert back is not None
    children = back.find_all(recursive=False)
    assert children[0].name == "i"
    assert "bi-arrow-left" in str(children[0].get("class"))
    assert "button-icon-start" in str(children[0].get("class"))
    assert "d-none" in back.select_one(".button-text").get("class", [])
    assert "d-sm-inline" in back.select_one(".button-text").get("class", [])


def test_mobile_share_and_navigation_actions_are_right_aligned_and_accessible(client):
    post = create_post()

    index_page = soup(client.get("/"))
    card_actions = index_page.select_one(".post-card-actions")
    card_children = card_actions.find_all(recursive=False)

    assert card_children[0].name == "a"
    assert card_children[0]["aria-label"] == "Читать далее"
    assert card_children[1].name == "button"
    assert "share-link-button-card" in str(card_children[1].get("class"))
    assert card_children[1]["aria-label"] == f"Скопировать ссылку на пост {post.title}"
    assert card_children[1].select_one("[data-share-feedback][aria-live='polite']") is not None

    detail_page = soup(client.get(post.get_absolute_url()))
    detail_actions = detail_page.select_one(".post-detail-bottom-actions")
    detail_children = detail_actions.find_all(recursive=False)

    assert len(detail_page.select("button.share-link-button-detail[data-share-copy]")) == 2
    assert detail_children[0].name == "button"
    assert "share-link-button-detail" in detail_children[0].get("class", [])
    assert detail_children[0].select_one("[data-share-feedback][aria-live='polite']") is not None
    assert detail_children[1].name == "a"
    assert detail_children[1]["aria-label"] == "Назад к списку"

    css = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")
    assert ".post-card-actions .share-link-button-card {\n    order: 1;" in css
    assert ".post-card-actions .btn {\n    order: 2;" in css
    assert ".post-detail-actions .share-link-button-detail {\n    display: none;" in css
    assert ".post-detail-bottom-actions .share-link-button-detail {\n    display: inline-flex;" in css
    assert ".post-card-actions .share-link-button-card [data-share-label]" in css
    assert ".post-detail-bottom-actions .share-link-button-detail [data-share-label]" in css
    mobile_contract = css.split("@media (max-width: 576px)", 1)[1]
    assert "display: flex;" in mobile_contract
    action_controls = mobile_contract.split(
        "  .post-card-actions .btn,\n"
        "  .post-card-actions .share-link-button-card,\n"
        "  .post-detail-bottom-actions .btn,\n"
        "  .post-detail-bottom-actions .share-link-button-detail {",
        1,
    )[1].split("\n  }\n\n  .post-card-actions .btn .button-icon", 1)[0]
    assert "width: 44px;" in action_controls
    assert "height: 44px;" in action_controls
    assert "min-width: 44px;" in action_controls
    assert "min-height: 44px;" in action_controls
    assert "padding: 0;" in action_controls
    assert "border: 1px solid var(--text-dark);" in action_controls
    assert "border-radius: 0.375rem;" in action_controls
    assert "background: var(--text-dark);" in action_controls
    assert "color: #fff;" in action_controls
    assert "box-shadow: none;" in action_controls
    assert "border-radius: 50%;" not in action_controls


@pytest.mark.parametrize(
    ("callout_type", "icon_class"),
    [
        ("note", "bi-sticky-fill"),
        ("AbStRaCt", "bi-card-text"),
        ("summary", "bi-card-text"),
        ("tldr", "bi-card-text"),
        ("info", "bi-info-circle-fill"),
        ("todo", "bi-check2-square"),
        ("tip", "bi-lightbulb-fill"),
        ("hint", "bi-lightbulb-fill"),
        ("important", "bi-exclamation-circle-fill"),
        ("success", "bi-check-circle-fill"),
        ("check", "bi-check-circle-fill"),
        ("done", "bi-check-circle-fill"),
        ("question", "bi-question-circle-fill"),
        ("help", "bi-question-circle-fill"),
        ("faq", "bi-question-circle-fill"),
        ("warning", "bi-exclamation-triangle-fill"),
        ("caution", "bi-exclamation-triangle-fill"),
        ("attention", "bi-exclamation-triangle-fill"),
        ("failure", "bi-x-octagon-fill"),
        ("fail", "bi-x-octagon-fill"),
        ("missing", "bi-x-octagon-fill"),
        ("danger", "bi-x-octagon-fill"),
        ("error", "bi-x-octagon-fill"),
        ("bug", "bi-bug-fill"),
        ("example", "bi-book-fill"),
        ("quote", "bi-quote"),
        ("cite", "bi-quote"),
    ],
)
def test_obsidian_callouts_render_official_types_with_semantic_title_and_body(
    callout_type, icon_class
):
    page = BeautifulSoup(
        convert_markdown_to_html(
            f"> [!{callout_type}] **Заголовок**\n"
            "> Текст выноски с `кодом` и [ссылкой](https://example.com)."
        ),
        "html.parser",
    )

    callout = page.select_one(f"aside.callout.callout-{callout_type.casefold()}")
    assert callout is not None
    assert callout["data-callout"] == callout_type.casefold()
    title = callout.select_one(".callout-title")
    body = callout.select_one(".callout-body")
    assert title is not None
    assert body is not None
    assert title.get_text(" ", strip=True) == "Заголовок"
    assert title.select_one("strong") is not None
    assert title.select_one(f"i.{icon_class}.callout-icon") is not None
    code = body.select_one("code")
    link = body.select_one("a")
    assert code is not None
    assert link is not None
    assert code.get_text(strip=True) == "кодом"
    assert link["href"] == "https://example.com"
    assert "[!" not in callout.get_text()


def test_obsidian_callout_unknown_type_uses_safe_note_fallback():
    page = BeautifulSoup(
        convert_markdown_to_html(
            "> [!CUSTOM-ALERT] Пользовательский заголовок\n> Безопасный текст"
        ),
        "html.parser",
    )

    callout = page.select_one("aside.callout.callout-note")
    assert callout is not None
    assert callout["data-callout"] == "note"
    title = callout.select_one(".callout-title")
    body = callout.select_one(".callout-body")
    assert title is not None
    assert body is not None
    assert title.get_text(" ", strip=True) == "Пользовательский заголовок"
    assert body.get_text(" ", strip=True) == "Безопасный текст"
    assert "[!" not in callout.get_text()


@pytest.mark.parametrize(("fold", "is_open"), [("+", True), ("-", False)])
def test_obsidian_folded_callouts_use_native_accessible_details(fold, is_open):
    page = BeautifulSoup(
        convert_markdown_to_html(
            f"> [!NOTE]{fold} **Складной заголовок**\n> Складное тело"
        ),
        "html.parser",
    )

    callout = page.select_one("details.callout.callout-note")
    assert callout is not None
    assert callout.has_attr("open") is is_open
    title = callout.select_one("summary .callout-title")
    body = callout.select_one(".callout-body")
    assert title is not None
    assert body is not None
    assert title.get_text(" ", strip=True) == "Складной заголовок"
    assert body.get_text(" ", strip=True) == "Складное тело"


def test_obsidian_callout_preserves_rich_and_nested_markdown_body():
    page = BeautifulSoup(
        convert_markdown_to_html(
            "> [!warning] **Внешний заголовок**\n"
            "> Текст со [ссылкой](https://example.com) и `кодом`.\n"
            ">\n"
            "> - Первый пункт\n"
            "> - Второй пункт\n"
            ">\n"
            "> > [!tip] Вложенный заголовок\n"
            "> > Вложенное тело"
        ),
        "html.parser",
    )

    outer = page.select_one("aside.callout-warning")
    assert outer is not None
    first_item = outer.select_one(".callout-body ul li")
    code = outer.select_one(".callout-body code")
    assert first_item is not None
    assert code is not None
    assert first_item.get_text(strip=True) == "Первый пункт"
    assert code.get_text(strip=True) == "кодом"
    nested = outer.select_one("aside.callout-tip")
    assert nested is not None
    nested_title = nested.select_one(".callout-title")
    nested_body = nested.select_one(".callout-body")
    assert nested_title is not None
    assert nested_body is not None
    assert nested_title.get_text(" ", strip=True) == "Вложенный заголовок"
    assert nested_body.get_text(" ", strip=True) == "Вложенное тело"


def test_plain_blockquotes_remain_blockquotes_and_callout_css_is_scoped():
    page = BeautifulSoup(convert_markdown_to_html("> Обычная цитата"), "html.parser")
    css = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")

    quote = page.select_one("blockquote.blockquote")
    assert quote is not None
    assert quote.get_text(strip=True) == "Обычная цитата"
    assert page.select_one("aside.callout, details.callout") is None
    assert ".markdown-content details.callout > .callout-summary" in css
    assert ".markdown-content details.callout > .callout-summary:focus-visible" in css


def test_detail_back_to_top_is_detail_only_ssr_anchor_with_progressive_script(client):
    post = create_post()

    detail_page = soup(client.get(post.get_absolute_url()))
    start = detail_page.select("h1#post-start[tabindex='-1']")
    controls = detail_page.select("a.post-back-to-top[data-back-to-top]")

    assert len(start) == 1
    assert len(controls) == 1
    control = controls[0]
    assert control["href"] == "#post-start"
    assert control["aria-label"] == "Вернуться к началу статьи"
    assert control.get_text(strip=True) == ""
    icon = control.select_one("i.bi-arrow-up[aria-hidden='true']")
    assert icon is not None
    assert "back-to-top.js" in str(detail_page)

    index_page = soup(client.get("/"))
    assert index_page.select("[data-back-to-top]") == []
    assert "back-to-top.js" not in str(index_page)

    js = (PROJECT_ROOT / "static/js/back-to-top.js").read_text(encoding="utf-8")
    assert "window.scrollY >= window.innerHeight" in js
    assert "getBoundingClientRect" in js
    assert "MutationObserver" in js
    assert "lightbox-overlay" in js
    assert "aria-hidden" in js
    assert "tabindex" in js
    assert "target.focus" in js
    assert "scrollIntoView" in js
    assert "role=\"button\"" not in js


def test_detail_mobile_action_pair_has_geometry_neutral_interaction_contract():
    css = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")
    contract = css.split("/* Mobile action-pair geometry contract */", 1)[1]

    assert "transition: background-color 0.2s ease, border-color 0.2s ease" in contract
    assert "transform: none;" in contract
    assert ".post-detail-bottom-actions .btn:focus-visible" in contract
    assert ".post-detail-bottom-actions .share-link-button-detail:focus-visible" in contract
    assert "outline-offset: 3px;" in contract


def test_detail_breadcrumbs_keep_mobile_current_accessible_and_desktop_truncated(client):
    category = Category.objects.create(name="Доступность", slug="accessibility")
    post = create_post(title="Очень длинный заголовок для проверки хлебных крошек",)
    post.category = category
    post.save(update_fields=["category"])

    page = soup(client.get(post.get_absolute_url()))
    breadcrumb = page.select_one("nav.breadcrumbs-dynamic")
    assert breadcrumb is not None
    roots = breadcrumb.select(".breadcrumbs-root")
    assert [root.get_text(strip=True) for root in roots] == ["Главная", "Доступность"]
    current = breadcrumb.select(".breadcrumbs-current[aria-current='page']")
    assert len(current) == 1
    assert current[0].get_text(strip=True) == post.title

    css = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")
    contract = css.split("/* Detail breadcrumb responsive contract */", 1)[1]
    assert "@media (max-width: 576px)" in contract
    assert "position: static;" in contract
    assert "min-height: 44px;" in contract
    assert "clip: rect(0, 0, 0, 0);" in contract
    assert ".breadcrumbs-section {\n    display: none;" in contract
    assert "@media (min-width: 577px)" in contract
    assert "text-overflow: ellipsis;" in contract


def test_back_to_top_css_keeps_ssr_fallback_and_reduced_motion_contract():
    css = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")
    contract = css.split("/* Detail return-to-top */", 1)[1]

    assert "width: 44px;" in contract
    assert "height: 44px;" in contract
    assert "z-index: 1010;" in contract
    assert "right: calc(1rem + env(safe-area-inset-right, 0px));" in contract
    assert "bottom: calc(5.25rem + env(safe-area-inset-bottom, 0px));" in contract
    assert "right: calc(1.5rem + env(safe-area-inset-right, 0px));" in contract
    assert "bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px));" in contract
    assert "@media (prefers-reduced-motion: reduce)" in contract
    assert "scroll-behavior: auto;" in contract
