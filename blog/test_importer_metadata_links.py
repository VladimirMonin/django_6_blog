from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.core.management import call_command
from django.core.management.base import CommandError

from blog.models import Post
from blog.services.obsidian_importer import (
    collect_broken_local_links,
    collect_local_media_references,
    import_obsidian_note_to_post,
)


pytestmark = pytest.mark.django_db


def write_note(tmp_path: Path, body: str) -> Path:
    note_path = tmp_path / "lesson.md"
    note_path.write_text(body, encoding="utf-8")
    return note_path


def test_import_requires_description_metadata(tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Урок без описания
---

Текст статьи.
""",
    )

    with pytest.raises(ValueError, match="description"):
        import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="no-description")


def test_description_metadata_is_saved_and_used_in_post_cards(client, tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Урок с описанием
description: Короткое описание для карточки.
---

Первый абзац статьи не должен попадать в карточку.
""",
    )

    post = import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="with-description")
    response = client.get("/")

    assert post.description == "Короткое описание для карточки."
    assert response.status_code == 200
    page = BeautifulSoup(response.content, "html.parser")
    card = page.select_one(".post-card")
    assert card is not None
    assert "Короткое описание для карточки." in card.get_text(" ")
    assert "Первый абзац статьи" not in card.get_text(" ")


def test_importer_collects_standard_markdown_and_obsidian_media_by_filename_and_stem(tmp_path):
    for filename in ["cover.webp", "diagram 01.png", "nested-photo.jpg"]:
        (tmp_path / filename).write_bytes(b"image")

    markdown = """
![[cover]]
![Схема](./diagram 01.png)
![Фото](nested-photo)
![Внешняя](https://example.com/external.png)
[Обычная ссылка](missing-page.md)
"""

    result = collect_local_media_references(markdown, tmp_path)

    assert [item.source_name for item in result.found] == ["cover", "diagram 01.png", "nested-photo"]
    assert [item.path.name for item in result.found] == ["cover.webp", "diagram 01.png", "nested-photo.jpg"]
    assert result.missing == []


def test_importer_reports_broken_local_media_links(tmp_path):
    markdown = "![[missing-cover]]\n![Нет](missing-image.png)"

    result = collect_local_media_references(markdown, tmp_path)

    assert result.found == []
    assert result.missing == ["missing-cover", "missing-image.png"]


def test_link_checker_reports_broken_standard_markdown_and_wiki_note_links(tmp_path):
    (tmp_path / "existing-note.md").write_text("ok", encoding="utf-8")
    markdown = """
[Есть](existing-note.md)
[[existing-note]]
[Нет](missing-note.md)
[[missing wiki note]]
[Внешняя](https://example.com/page)
"""

    assert collect_broken_local_links(markdown, tmp_path) == ["missing-note.md", "missing wiki note"]


def test_import_copies_standard_markdown_and_wiki_media_and_renders_urls(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    (tmp_path / "cover.webp").write_bytes(b"RIFFxxxxWEBP")
    (tmp_path / "diagram.png").write_bytes(b"PNG")
    note_path = write_note(
        tmp_path,
        """---
title: Медиа урок
description: Короткое описание медиа урока.
---

![[cover]]
![Схема](diagram.png)
""",
    )

    post = import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="media-lesson")

    assert post.media_files.count() == 2
    assert "![[" not in post.content_html
    assert post.content_html.count("/media/posts/media-lesson/") == 2


def test_import_command_can_check_links_without_creating_post(tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Проверка ссылок
description: CLI только проверяет ссылки.
---

![[missing-cover]]
""",
    )

    with pytest.raises(CommandError, match="Broken local links"):
        call_command("import_obsidian_note", note_path, assets_dir=tmp_path, check_links=True)

    assert Post.objects.count() == 0
