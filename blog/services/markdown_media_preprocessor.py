"""Resolve post media references in Markdown before HTML conversion."""

import re
from html import escape
from pathlib import PurePosixPath
from urllib.parse import urlparse


class MarkdownMediaPreprocessor:
    """Convert Obsidian and local Markdown media links into Django media URLs."""

    OBSIDIAN_IMAGE_RE = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
    MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def __init__(self, post):
        self.post = post
        self._media_by_name = self._build_media_map()

    def process(self, markdown_text: str) -> str:
        if not markdown_text or not self.post or not getattr(self.post, "pk", None):
            return markdown_text

        markdown_text = self.convert_wikilinks(markdown_text)
        return self.resolve_local_links(markdown_text)

    def convert_wikilinks(self, markdown_text: str) -> str:
        def replace(match):
            target = match.group(1).strip()
            alt_text = (match.group(2) or self._display_name(target)).strip()
            media = self._resolve_media(target)
            if not media:
                return f"![{alt_text}]({target})"
            return self._render_media_embed(media, alt_text)

        return self.OBSIDIAN_IMAGE_RE.sub(replace, markdown_text)

    def resolve_local_links(self, markdown_text: str) -> str:
        def replace(match):
            alt_text = match.group(1)
            target = match.group(2).strip()
            if self._is_external_or_absolute(target):
                return match.group(0)
            url = self._resolve_media_url(target)
            if not url:
                return match.group(0)
            return f"![{alt_text}]({url})"

        return self.MARKDOWN_IMAGE_RE.sub(replace, markdown_text)

    def _build_media_map(self):
        media_map = {}
        if not self.post or not getattr(self.post, "pk", None):
            return media_map

        for media in self.post.media_files.all():
            names = {media.original_filename, media.file_slug, PurePosixPath(media.file.name).name}
            for key in names:
                if not key:
                    continue
                path = PurePosixPath(key)
                for alias in {path.name, path.stem}:
                    if alias:
                        media_map[self._normalize_path(alias)] = media
        return media_map

    def _resolve_media_url(self, target):
        media = self._resolve_media(target)
        if media:
            return media.file.url
        return None

    def _resolve_media(self, target):
        normalized = self._normalize_path(target)
        return self._media_by_name.get(normalized)

    @staticmethod
    def _render_media_embed(media, alt_text):
        url = media.file.url
        escaped_alt = escape(alt_text, quote=True)
        escaped_url = escape(url, quote=True)
        if media.media_type == "image":
            return f"![{alt_text}]({url})"
        if media.media_type == "audio":
            return f'<audio controls src="{escaped_url}">{escaped_alt}</audio>'
        if media.media_type == "video":
            return f'<video controls src="{escaped_url}">{escaped_alt}</video>'
        return f"[{alt_text}]({url})"

    @staticmethod
    def _display_name(target):
        return PurePosixPath(target).name

    @staticmethod
    def _normalize_path(target):
        path = PurePosixPath(target.strip())
        return path.name.casefold()

    @staticmethod
    def _is_external_or_absolute(target):
        parsed = urlparse(target)
        return bool(parsed.scheme or parsed.netloc or target.startswith("/"))
