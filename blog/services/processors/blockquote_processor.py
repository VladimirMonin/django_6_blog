# blog/services/processors/blockquote_processor.py
"""Преобразовывает цитаты и Obsidian callout в безопасную HTML-структуру."""

import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

from blog.services.html_processor import HTMLProcessor


class BlockquoteProcessor(HTMLProcessor):
    """Рендерит полный контракт Obsidian callout, не меняя обычные цитаты."""

    CALLOUT_PATTERN = re.compile(
        r"^\s*\[!(?P<callout_type>[a-z0-9_-]+)\](?P<fold>[+-]?)(?P<space>[ \t]*)",
        re.IGNORECASE,
    )
    CALLOUT_STYLES = {
        "note": ("alert-secondary", "bi-sticky-fill"),
        "abstract": ("alert-info", "bi-card-text"),
        "summary": ("alert-info", "bi-card-text"),
        "tldr": ("alert-info", "bi-card-text"),
        "info": ("alert-info", "bi-info-circle-fill"),
        "todo": ("alert-info", "bi-check2-square"),
        "tip": ("alert-primary", "bi-lightbulb-fill"),
        "hint": ("alert-primary", "bi-lightbulb-fill"),
        "important": ("alert-warning", "bi-exclamation-circle-fill"),
        "success": ("alert-success", "bi-check-circle-fill"),
        "check": ("alert-success", "bi-check-circle-fill"),
        "done": ("alert-success", "bi-check-circle-fill"),
        "question": ("alert-warning", "bi-question-circle-fill"),
        "help": ("alert-warning", "bi-question-circle-fill"),
        "faq": ("alert-warning", "bi-question-circle-fill"),
        "warning": ("alert-warning", "bi-exclamation-triangle-fill"),
        "caution": ("alert-warning", "bi-exclamation-triangle-fill"),
        "attention": ("alert-warning", "bi-exclamation-triangle-fill"),
        "failure": ("alert-danger", "bi-x-octagon-fill"),
        "fail": ("alert-danger", "bi-x-octagon-fill"),
        "missing": ("alert-danger", "bi-x-octagon-fill"),
        "danger": ("alert-danger", "bi-x-octagon-fill"),
        "error": ("alert-danger", "bi-x-octagon-fill"),
        "bug": ("alert-danger", "bi-bug-fill"),
        "example": ("alert-primary", "bi-book-fill"),
        "quote": ("alert-secondary", "bi-quote"),
        "cite": ("alert-secondary", "bi-quote"),
    }

    def process(self, soup: BeautifulSoup) -> None:
        """Заменяет callout на semantic HTML и оставляет обычные цитаты цитатами."""
        for blockquote in list(soup.find_all("blockquote")):
            first_paragraph = blockquote.find("p", recursive=False)
            if first_paragraph is None:
                self._style_plain_blockquote(blockquote)
                continue
            marker_node = self._first_text_node(first_paragraph)
            if marker_node is None:
                self._style_plain_blockquote(blockquote)
                continue
            match = self.CALLOUT_PATTERN.match(str(marker_node))

            if match is None:
                self._style_plain_blockquote(blockquote)
                continue

            self._render_callout(soup, blockquote, first_paragraph, marker_node, match)

    @staticmethod
    def _first_text_node(paragraph: Tag | None) -> NavigableString | None:
        if paragraph is None:
            return None
        return next(
            (
                node
                for node in paragraph.contents
                if isinstance(node, NavigableString) and node.strip()
            ),
            None,
        )

    @staticmethod
    def _style_plain_blockquote(blockquote: Tag) -> None:
        if "class" not in blockquote.attrs:
            blockquote["class"] = "blockquote border-start border-warning ps-3"

    def _render_callout(
        self,
        soup: BeautifulSoup,
        blockquote: Tag,
        first_paragraph: Tag,
        marker_node: NavigableString,
        match: re.Match[str],
    ) -> None:
        source_type = match["callout_type"].casefold()
        known_type = source_type in self.CALLOUT_STYLES
        rendered_type = source_type if known_type else "note"
        alert_class, icon_class = self.CALLOUT_STYLES.get(
            source_type, self.CALLOUT_STYLES["note"]
        )
        remainder = str(marker_node)[match.end() :]
        if remainder:
            marker_node.replace_with(NavigableString(remainder))
        else:
            marker_node.extract()

        paragraph_nodes = list(first_paragraph.contents)
        first_break = next(
            (
                index
                for index, node in enumerate(paragraph_nodes)
                if getattr(node, "name", None) == "br"
            ),
            None,
        )
        title_nodes = (
            paragraph_nodes[:first_break]
            if first_break is not None
            else paragraph_nodes
        )
        inline_body_nodes = (
            paragraph_nodes[first_break + 1 :] if first_break is not None else []
        )
        title = self._build_title(
            soup,
            title_nodes,
            icon_class,
            source_type.replace("-", " ").title() if known_type else "Note",
        )
        body = soup.new_tag("div", attrs={"class": "callout-body"})
        if inline_body_nodes:
            inline_body = soup.new_tag("p")
            for node in inline_body_nodes:
                inline_body.append(node.extract())
            body.append(inline_body)

        first_paragraph.extract()
        for child in list(blockquote.contents):
            body.append(child.extract())

        is_folded = bool(match["fold"])
        callout = soup.new_tag("details" if is_folded else "aside")
        callout["class"] = " ".join(
            ["alert", alert_class, "callout", f"callout-{rendered_type}"]
        )
        callout["data-callout"] = rendered_type
        if is_folded:
            if match["fold"] == "+":
                callout["open"] = ""
            summary = soup.new_tag("summary", attrs={"class": "callout-summary"})
            summary.append(title)
            callout.append(summary)
        else:
            callout["role"] = "note"
            callout["aria-label"] = title.get_text(" ", strip=True)
            callout.append(title)
        callout.append(body)
        blockquote.replace_with(callout)

    @staticmethod
    def _build_title(
        soup: BeautifulSoup,
        title_nodes: list[PageElement],
        icon_class: str,
        default_title: str,
    ) -> Tag:
        title = soup.new_tag(
            "div", attrs={"class": "callout-title fw-semibold mb-2"}
        )
        icon = soup.new_tag("i", attrs={"class": f"bi {icon_class} callout-icon"})
        icon["aria-hidden"] = "true"
        title.append(icon)
        if title_nodes:
            title.append(" ")
            for node in title_nodes:
                title.append(node.extract())
        else:
            title.append(f" {default_title}")
        return title

    def get_name(self) -> str:
        """Возвращает имя процессора для логирования.

        Returns:
            Строка с названием процессора.
        """
        return "BlockquoteProcessor"
