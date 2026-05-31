from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError

from blog.content_import.obsidian import import_obsidian_note_to_post, resolve_cover_reference
from blog.content_import.timecodes import extract_timecode_blocks, parse_timecodes
from blog.models import Post
from blog.services.markdown_converter import convert_markdown_to_html


pytestmark = pytest.mark.django_db


def write_note(tmp_path: Path, body: str) -> Path:
    note_path = tmp_path / "media-note.md"
    note_path.write_text(body, encoding="utf-8")
    return note_path


def page_soup(response):
    return BeautifulSoup(response.content, "html.parser")


def test_parse_timecodes_accepts_multiline_markdown_fence_format():
    entries = parse_timecodes(
        """
00:00 Вступление
01:23 — Главная мысль
1:02:03 | Ответы на вопросы
bad line is ignored
        """
    )

    assert entries == [
        {"time": "00:00", "seconds": 0, "label": "Вступление"},
        {"time": "01:23", "seconds": 83, "label": "Главная мысль"},
        {"time": "1:02:03", "seconds": 3723, "label": "Ответы на вопросы"},
    ]


def test_extract_timecode_blocks_returns_entries_and_removes_fences_from_body():
    markdown, entries = extract_timecode_blocks(
        """# Видео урок

Текст до блока.

```timecodes
00:00 Начало
00:45 Демонстрация
```

Текст после блока.
"""
    )

    assert entries == [
        {"time": "00:00", "seconds": 0, "label": "Начало"},
        {"time": "00:45", "seconds": 45, "label": "Демонстрация"},
    ]
    assert "```timecodes" not in markdown
    assert "00:45 Демонстрация" not in markdown
    assert "Текст до блока." in markdown
    assert "Текст после блока." in markdown


def test_importer_reads_content_type_media_url_and_timecodes_from_frontmatter(tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Видео выпуск
description: Описание видео выпуска.
type: video
media_url: https://cdn.example.test/video.mp4
tags: [django, video]
---

# Видео выпуск

Вводный текст.

```timecodes
00:00 Начало
02:15 Практика
```
""",
    )

    post = import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="video-episode")

    assert post.content_type == Post.ContentType.VIDEO
    assert post.media_url == "https://cdn.example.test/video.mp4"
    assert post.timecodes == [
        {"time": "00:00", "seconds": 0, "label": "Начало"},
        {"time": "02:15", "seconds": 135, "label": "Практика"},
    ]
    assert "```timecodes" not in post.content
    assert [tag.name for tag in post.tags.order_by("name")] == ["Django", "Video"]


def test_import_command_accepts_content_type_and_media_url_overrides(tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Аудио заметка
description: Описание аудио.
---

Текст.
""",
    )

    call_command(
        "import_obsidian_note",
        note_path,
        assets_dir=tmp_path,
        slug="audio-note",
        content_type="audio",
        media_url="https://cdn.example.test/audio.mp3",
    )

    post = Post.objects.get(slug="audio-note")
    assert post.content_type == Post.ContentType.AUDIO
    assert post.media_url == "https://cdn.example.test/audio.mp3"


def test_create_content_note_template_command_writes_media_note_with_timecodes(tmp_path):
    note_path = tmp_path / "podcast.md"

    call_command(
        "create_content_note",
        note_path,
        title="Подкаст выпуск 1",
        description="Короткое описание подкаста.",
        content_type="podcast",
        tags="django,agents",
        media_url="https://cdn.example.test/podcast.mp3",
    )

    text = note_path.read_text(encoding="utf-8")
    assert 'title: "Подкаст выпуск 1"' in text
    assert 'description: "Короткое описание подкаста."' in text
    assert "type: podcast" in text
    assert "media_url: https://cdn.example.test/podcast.mp3" in text
    assert "tags: [django, agents]" in text
    assert "```timecodes" in text
    assert "00:00 Вступление" in text



def test_list_card_shows_content_type_badge_for_media_posts(client):
    Post.objects.create(
        title="Подкаст в списке",
        description="Описание подкаста.",
        content_type=Post.ContentType.PODCAST,
        media_url="https://cdn.example.test/podcast.mp3",
        content="Текст.",
        status=Post.Status.PUBLISHED,
    )

    response = client.get("/")

    assert response.status_code == 200
    page = page_soup(response)
    badge = page.select_one(".post-badge-type-podcast")
    assert badge is not None
    assert "Подкаст" in badge.get_text(" ", strip=True)
    assert badge.select_one(".bi-broadcast-pin") is not None


def test_media_import_rejects_invalid_timecode_line_for_media_posts(tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Видео с плохими таймкодами
description: Описание видео.
type: video
media_url: https://cdn.example.test/video.mp4
---

# Видео с плохими таймкодами

```timecodes
00:00 Начало
not-a-timecode строка
03:99 Некорректные секунды
```
""",
    )

    with pytest.raises(ValueError, match="Invalid timecode"):
        import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="bad-video")

    assert not Post.objects.filter(slug="bad-video").exists()


def test_model_save_rejects_invalid_media_timecodes_before_db_write():
    with pytest.raises(ValidationError, match="Invalid timecode"):
        Post.objects.create(
            title="Видео с невалидными JSON-таймкодами",
            description="Описание.",
            content_type=Post.ContentType.VIDEO,
            media_url="https://cdn.example.test/video.mp4",
            timecodes=[{"time": "03:99", "seconds": 239, "label": "Плохие секунды"}],
            content="Текст.",
            status=Post.Status.PUBLISHED,
        )

    assert not Post.objects.filter(title="Видео с невалидными JSON-таймкодами").exists()



def test_import_command_reports_timecode_validation_errors(tmp_path):
    note_path = write_note(
        tmp_path,
        """---
title: Аудио с плохими таймкодами
description: Описание аудио.
type: audio
media_url: https://cdn.example.test/audio.mp3
---

```timecodes
00:00 Начало
wrong line
```
""",
    )

    with pytest.raises(CommandError, match="Invalid timecode"):
        call_command("import_obsidian_note", note_path, assets_dir=tmp_path, slug="bad-audio")


def test_importer_uses_frontmatter_cover_as_card_cover_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media-root"
    cover = tmp_path / "cover.webp"
    cover.write_bytes(b"RIFFxxxxWEBP")
    note_path = write_note(
        tmp_path,
        """---
title: Пост с обложкой
description: Описание с обложкой.
type: video
media_url: https://cdn.example.test/video.mp4
cover: cover.webp
---

# Пост с обложкой

Текст без изображения в теле.
""",
    )

    post = import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="with-cover")

    assert post.cover_media is not None
    assert post.cover_media.original_filename == "cover.webp"
    assert post.cover_media.media_type == "image"


def test_importer_rejects_cover_paths_outside_assets_dir(tmp_path):
    outside_cover = tmp_path.parent / "outside-cover.webp"
    outside_cover.write_bytes(b"RIFFxxxxWEBP")

    with pytest.raises(ValueError, match="Cover path must stay inside assets_dir"):
        resolve_cover_reference(str(outside_cover), tmp_path)

    with pytest.raises(ValueError, match="Cover path must stay inside assets_dir"):
        resolve_cover_reference("../outside-cover.webp", tmp_path)



def test_create_content_note_template_command_writes_cover_metadata(tmp_path):
    note_path = tmp_path / "video.md"

    call_command(
        "create_content_note",
        note_path,
        title="Видео с обложкой",
        description="Короткое описание.",
        content_type="video",
        tags="django",
        media_url="https://cdn.example.test/video.mp4",
        cover="cover.webp",
    )

    text = note_path.read_text(encoding="utf-8")
    assert "cover: cover.webp" in text


def test_mermaid_library_scripts_are_loaded_before_project_initializer(client):
    response = client.get("/")
    html = response.content.decode()

    assert html.index("mermaid.min.js") < html.index("init-libs.js")
    assert html.index("svg-pan-zoom.min.js") < html.index("init-libs.js")


def test_mermaid_markdown_renders_panzoom_shell_and_toolbar():
    html = convert_markdown_to_html(
        """```mermaid
graph TD
    A[\"Старт\"] --> B[\"Финиш\"]
```"""
    )

    assert 'class="mermaid-panzoom-shell"' in html
    assert 'class="mermaid-toolbar"' in html
    assert 'class="mermaid"' in html
    assert "mermaid-panzoom-fullscreen" in html


def test_mermaid_markdown_escapes_source_html_to_avoid_xss():
    html = convert_markdown_to_html(
        """```mermaid
graph TD
    A[<script>alert(1)</script>] --> B[ok]
```"""
    )

    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one(".mermaid-panzoom-shell .mermaid") is not None
    assert soup.select_one("script") is None
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html



def test_video_detail_renders_media_player_and_clickable_timecodes(client):
    post = Post.objects.create(
        title="Видео с таймкодами",
        description="Описание видео.",
        content_type=Post.ContentType.VIDEO,
        media_url="https://cdn.example.test/video.mp4",
        timecodes=[
            {"time": "00:00", "seconds": 0, "label": "Начало"},
            {"time": "03:20", "seconds": 200, "label": "Демо"},
        ],
        content="Основной текст.",
        status=Post.Status.PUBLISHED,
    )

    response = client.get(post.get_absolute_url())

    assert response.status_code == 200
    page = page_soup(response)
    player = page.select_one("video.post-media-player")
    assert player is not None
    assert player["src"] == "https://cdn.example.test/video.mp4"
    assert player["data-timecode-player"] == "post-media-player"
    buttons = page.select("button.timecode-button")
    assert [button["data-seek-seconds"] for button in buttons] == ["0", "200"]
    assert [button.get_text(" ", strip=True) for button in buttons] == [
        "00:00 Начало",
        "03:20 Демо",
    ]
    assert "timecodes.js" in response.content.decode()


def test_audio_and_podcast_detail_render_audio_player(client):
    for content_type in [Post.ContentType.AUDIO, Post.ContentType.PODCAST]:
        post = Post.objects.create(
            title=f"{content_type} выпуск",
            description="Описание.",
            content_type=content_type,
            media_url="https://cdn.example.test/audio.mp3",
            timecodes=[{"time": "00:05", "seconds": 5, "label": "Сегмент"}],
            content="Текст.",
            status=Post.Status.PUBLISHED,
        )

        response = client.get(post.get_absolute_url())
        page = page_soup(response)
        player = page.select_one("audio.post-media-player")
        assert response.status_code == 200
        assert player is not None
        assert player["src"] == "https://cdn.example.test/audio.mp3"
        assert page.select_one("button.timecode-button")["data-seek-seconds"] == "5"
