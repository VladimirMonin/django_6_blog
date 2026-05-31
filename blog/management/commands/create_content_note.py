"""Create Markdown templates for article/video/audio/podcast posts."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a Markdown note template for article, video, audio, or podcast content."

    def add_arguments(self, parser):
        parser.add_argument("note", type=Path, help="Destination Markdown file path")
        parser.add_argument("--title", required=True, help="Post title")
        parser.add_argument("--description", required=True, help="Post/card description")
        parser.add_argument(
            "--content-type",
            choices=["article", "video", "audio", "podcast"],
            default="article",
            help="Content type for frontmatter type field.",
        )
        parser.add_argument("--tags", default="", help="Comma-separated tags")
        parser.add_argument("--media-url", default="", help="External audio/video URL")
        parser.add_argument("--cover", default="", help="Cover image filename/path for frontmatter")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the destination file if it already exists.",
        )

    def handle(self, *args, **options):
        note_path: Path = options["note"].expanduser().resolve()
        if note_path.suffix.lower() != ".md":
            raise CommandError(f"Expected a Markdown file path: {note_path}")
        if note_path.exists() and not options["force"]:
            raise CommandError(f"File already exists: {note_path}. Re-run with --force to overwrite.")

        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(
            build_note_template(
                title=options["title"],
                description=options["description"],
                content_type=options["content_type"],
                tags=options["tags"],
                media_url=options["media_url"],
                cover=options["cover"],
            ),
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"Created content note template: {note_path}"))


def build_note_template(
    *,
    title: str,
    description: str,
    content_type: str,
    tags: str = "",
    media_url: str = "",
    cover: str = "",
) -> str:
    tag_items = [tag.strip().lstrip("#") for tag in tags.split(",") if tag.strip()]
    tags_line = f"tags: [{', '.join(tag_items)}]" if tag_items else "tags: []"
    media_line = f"media_url: {media_url}\n" if media_url else ""
    cover_line = f"cover: {cover}\n" if cover else ""
    timecodes_block = ""
    if content_type in {"video", "audio", "podcast"}:
        timecodes_block = """
```timecodes
00:00 Вступление
01:30 Основная часть
03:00 Итоги
```
"""

    return f"""---
title: \"{title}\"
description: \"{description}\"
type: {content_type}
{media_line}{cover_line}{tags_line}
---

# {title}

Короткое вступление к материалу.
{timecodes_block}
Основной текст публикации.
"""
