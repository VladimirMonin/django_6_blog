from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from blog.content_import.media_bundle import collect_note_media_bundle, iter_media_targets_for_bundle
from blog.models import Post
from blog.services.obsidian_importer import import_obsidian_note_to_post


def test_collect_note_assets_supports_obsidian_and_markdown_paths(tmp_path):
    vault = tmp_path / "vault"
    lesson_dir = vault / "10_Lessons" / "LM Studio"
    media_dir = vault / "999_files" / "lm-studio"
    lesson_dir.mkdir(parents=True)
    media_dir.mkdir(parents=True)
    (media_dir / "cover-01.webp").write_bytes(b"cover")
    (media_dir / "diagram 01.png").write_bytes(b"diagram")
    (lesson_dir / "local.jpg").write_bytes(b"local")
    note = lesson_dir / "lesson.md"
    note.write_text(
        """---
title: Старый тайтл
---

![[999_files/lm-studio/cover-01.webp|500]]
![Схема](../../999_files/lm-studio/diagram%2001.png)
![Локальная](local.jpg)
""",
        encoding="utf-8",
    )

    result = collect_note_media_bundle(
        note,
        tmp_path / "bundle",
        vault_root=vault,
        title="Новый тайтл",
        description="Описание для карточки.",
    )

    assert result.missing == []
    assert [item.copied_path.name for item in result.copied] == [
        "cover-01.webp",
        "diagram 01.png",
        "local.jpg",
    ]
    assert result.note_path is not None
    copied_note = result.note_path.read_text(encoding="utf-8")
    assert 'title: "Новый тайтл"' in copied_note
    assert 'description: "Описание для карточки."' in copied_note


def test_collect_note_assets_reports_missing_media(tmp_path):
    note = tmp_path / "lesson.md"
    note.write_text("![[missing.webp]]", encoding="utf-8")

    result = collect_note_media_bundle(note, tmp_path / "bundle")

    assert result.missing == ["missing.webp"]
    assert result.copied == []


def test_iter_media_targets_preserves_paths_for_bundle():
    markdown = """
![[999_files/lm-studio/cover-01.webp|500]]
![Image](../media/image one.png)
![External](https://example.com/image.png)
"""

    assert list(iter_media_targets_for_bundle(markdown)) == [
        "999_files/lm-studio/cover-01.webp",
        "../media/image one.png",
    ]


@pytest.mark.django_db
def test_collect_command_bundle_can_be_imported_with_title_and_first_image_cover(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media-root"
    vault = tmp_path / "vault"
    lesson_dir = vault / "10_Lessons" / "LM Studio"
    media_dir = vault / "999_files" / "lm-studio"
    lesson_dir.mkdir(parents=True)
    media_dir.mkdir(parents=True)
    (media_dir / "cover-01.webp").write_bytes(b"RIFFxxxxWEBP")
    (media_dir / "second.png").write_bytes(b"PNG")
    note = lesson_dir / "lesson.md"
    note.write_text(
        """---
title: Старый заголовок
series: lm-studio-course
tags: [lm-studio]
---

![[999_files/lm-studio/cover-01.webp|500]]
![Вторая](../../999_files/lm-studio/second.png)
""",
        encoding="utf-8",
    )
    bundle_dir = tmp_path / "assets"

    call_command(
        "collect_note_assets",
        note,
        bundle_dir,
        vault_root=vault,
        title="LM Studio: урок 1",
        description="Проверочное описание.",
    )
    post = import_obsidian_note_to_post(
        bundle_dir / "lesson.md",
        assets_dir=bundle_dir,
        slug="lm-studio-urok-1",
    )

    assert post.title == "LM Studio: урок 1"
    assert post.description == "Проверочное описание."
    assert post.cover_media is not None
    assert post.cover_media.original_filename == "cover-01.webp"
    assert [media.original_filename for media in post.media_files.all()] == [
        "cover-01.webp",
        "second.png",
    ]


@pytest.mark.django_db
def test_import_command_accepts_title_and_description_overrides(tmp_path):
    note = tmp_path / "lesson.md"
    note.write_text("---\ntitle: Старый\n---\n\nТекст", encoding="utf-8")

    call_command(
        "import_obsidian_note",
        note,
        assets_dir=tmp_path,
        slug="override-post",
        title="Новый заголовок",
        description="Описание из CLI.",
    )

    post = Post.objects.get(slug="override-post")
    assert post.title == "Новый заголовок"
    assert post.description == "Описание из CLI."


def test_collect_command_raises_when_missing_media(tmp_path):
    note = tmp_path / "lesson.md"
    note.write_text("![[missing.webp]]", encoding="utf-8")

    with pytest.raises(CommandError, match="Some local media references"):
        call_command("collect_note_assets", note, tmp_path / "bundle")
