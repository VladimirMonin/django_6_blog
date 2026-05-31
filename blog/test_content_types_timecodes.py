from pathlib import Path
import shutil

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError

from blog.content_import.obsidian import import_obsidian_note_to_post, resolve_cover_reference
from blog.content_import.timecodes import extract_timecode_blocks, parse_timecodes
from blog.models import Post, PostMedia
from blog.services.markdown_converter import convert_markdown_to_html


pytestmark = pytest.mark.django_db

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_LM_STUDIO_OPUS = (
    PROJECT_ROOT
    / "tests"
    / "assets"
    / "obsidian"
    / "lm-studio-lesson-01"
    / "01_Как_нейросети_превращают_слова_в_геометрию.opus"
)
HERMES_YOUTUBE_ASSET_DIR = PROJECT_ROOT / "tests" / "assets" / "youtube" / "hermes-six-features"
HERMES_YOUTUBE_VIDEO_NOTE = HERMES_YOUTUBE_ASSET_DIR / "hermes-six-features-video.md"
HERMES_YOUTUBE_PODCAST_NOTE = HERMES_YOUTUBE_ASSET_DIR / "hermes-six-features-podcast.md"
HERMES_YOUTUBE_VIDEO = HERMES_YOUTUBE_ASSET_DIR / "hermes-six-features.mp4"
HERMES_YOUTUBE_AUDIO = HERMES_YOUTUBE_ASSET_DIR / "hermes-six-features.opus"


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



def test_list_card_shows_content_type_badge_for_all_post_types(client):
    expected = [
        (Post.ContentType.ARTICLE, "Статья", "bi-file-text"),
        (Post.ContentType.VIDEO, "Видео", "bi-camera-video"),
        (Post.ContentType.AUDIO, "Аудио", "bi-soundwave"),
        (Post.ContentType.PODCAST, "Подкаст", "bi-broadcast-pin"),
    ]
    for content_type, label, _icon in expected:
        Post.objects.create(
            title=f"{label} в списке",
            description=f"Описание: {label}.",
            content_type=content_type,
            media_url="https://cdn.example.test/media.mp3" if content_type != Post.ContentType.ARTICLE else "",
            content="Текст.",
            status=Post.Status.PUBLISHED,
        )

    response = client.get("/")

    assert response.status_code == 200
    page = page_soup(response)
    for content_type, label, icon in expected:
        badge = page.select_one(f".post-badge-type-{content_type}")
        assert badge is not None
        assert label in badge.get_text(" ", strip=True)
        assert badge.select_one(f".{icon}") is not None


def test_list_card_uses_unified_default_cover_placeholders_for_all_post_types(client):
    expected = [
        (Post.ContentType.ARTICLE, "bi-journal-code"),
        (Post.ContentType.VIDEO, "bi-camera-video"),
        (Post.ContentType.AUDIO, "bi-soundwave"),
        (Post.ContentType.PODCAST, "bi-broadcast-pin"),
    ]
    for content_type, _icon in expected:
        Post.objects.create(
            title=f"{content_type} без обложки",
            description="Описание.",
            content_type=content_type,
            media_url="https://cdn.example.test/media.mp3" if content_type != Post.ContentType.ARTICLE else "",
            content="Текст.",
            status=Post.Status.PUBLISHED,
        )

    response = client.get("/")

    assert response.status_code == 200
    page = page_soup(response)
    for content_type, icon in expected:
        cover = page.select_one(f".post-card-cover-placeholder-{content_type}")
        assert cover is not None
        assert "post-card-cover-placeholder" in cover["class"]
        assert cover.select_one(f".{icon}") is not None


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
    timecode_panel = page.select_one(".timecode-list")
    assert timecode_panel is not None
    assert page.select_one(".timecode-list-header .timecode-list-icon") is not None
    assert "Клик по пункту перематывает плеер" in timecode_panel.get_text(" ", strip=True)
    assert page.select_one(".timecode-grid") is not None
    assert "btn-outline-dark" not in response.content.decode()


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


def test_imported_podcast_uses_embedded_local_audio_as_player_source(tmp_path, settings, client):
    if not REAL_LM_STUDIO_OPUS.exists():
        pytest.skip("Real LM Studio opus fixture is stored in ignored tests/assets/ and is unavailable.")
    settings.MEDIA_ROOT = tmp_path / "media-root"
    audio = tmp_path / REAL_LM_STUDIO_OPUS.name
    shutil.copyfile(REAL_LM_STUDIO_OPUS, audio)
    assert audio.stat().st_size > 1_000_000
    note_path = write_note(
        tmp_path,
        f"""---
title: Реальный локальный подкаст
description: Подкаст с реальным Opus-файлом LM Studio и таймкодами.
type: podcast
---

# Реальный локальный подкаст

![[{REAL_LM_STUDIO_OPUS.name}]]

```timecodes
00:00 Вступление
01:58 Что такое модель
```
""",
    )

    post = import_obsidian_note_to_post(note_path, assets_dir=tmp_path, slug="local-podcast")

    assert post.media_url == ""
    assert post.primary_media is not None
    assert post.primary_media.original_filename == REAL_LM_STUDIO_OPUS.name
    assert post.primary_media.media_type == PostMedia.MediaType.AUDIO
    assert post.primary_media.file.size == REAL_LM_STUDIO_OPUS.stat().st_size
    assert post.timecodes[1] == {"time": "01:58", "seconds": 118, "label": "Что такое модель"}

    response = client.get(post.get_absolute_url())
    page = page_soup(response)
    player = page.select_one("audio.post-media-player")
    assert response.status_code == 200
    assert player is not None
    assert len(page.select("audio")) == 1
    assert page.select_one(".markdown-content audio") is None
    assert player["src"].endswith("/media/posts/local-podcast/01-kak-neyroseti-prevrashchayut-slova-v-geometriyu.opus")
    assert [button["data-seek-seconds"] for button in page.select("button.timecode-button")] == ["0", "118"]


def test_imported_hermes_youtube_video_uses_real_downloaded_mp4_as_player_source(tmp_path, settings, client):
    if not HERMES_YOUTUBE_VIDEO_NOTE.exists() or not HERMES_YOUTUBE_VIDEO.exists():
        pytest.skip("Real Hermes YouTube video fixture is stored in ignored tests/assets/ and is unavailable.")
    settings.MEDIA_ROOT = tmp_path / "media-root"

    post = import_obsidian_note_to_post(
        HERMES_YOUTUBE_VIDEO_NOTE,
        assets_dir=HERMES_YOUTUBE_ASSET_DIR,
        slug="hermes-six-features-video",
    )

    assert post.content_type == Post.ContentType.VIDEO
    assert post.media_url == ""
    assert post.primary_media is not None
    assert post.primary_media.original_filename == "hermes-six-features.mp4"
    assert post.primary_media.media_type == PostMedia.MediaType.VIDEO
    assert post.primary_media.file.size == HERMES_YOUTUBE_VIDEO.stat().st_size
    assert post.cover_media is not None
    assert post.cover_media.original_filename == "hermes-six-features.webp"
    assert post.timecodes == [
        {"time": "0:00", "seconds": 0, "label": "Вступление"},
        {"time": "1:16", "seconds": 76, "label": "Фича 1"},
        {"time": "2:57", "seconds": 177, "label": "Фича 2"},
        {"time": "4:56", "seconds": 296, "label": "Фича 3"},
        {"time": "6:15", "seconds": 375, "label": "Фича 4"},
        {"time": "7:38", "seconds": 458, "label": "Фича 5"},
        {"time": "8:48", "seconds": 528, "label": "Фича 6"},
    ]

    response = client.get(post.get_absolute_url())
    page = page_soup(response)
    player = page.select_one("video.post-media-player")
    assert response.status_code == 200
    assert player is not None
    assert len(page.select("video")) == 1
    assert page.select_one(".markdown-content video") is None
    assert player["src"].endswith("/media/posts/hermes-six-features-video/hermes-six-features.mp4")
    assert [button["data-seek-seconds"] for button in page.select("button.timecode-button")] == [
        "0", "76", "177", "296", "375", "458", "528"
    ]


def test_imported_hermes_youtube_podcast_uses_extracted_opus_as_player_source(tmp_path, settings, client):
    if not HERMES_YOUTUBE_PODCAST_NOTE.exists() or not HERMES_YOUTUBE_AUDIO.exists():
        pytest.skip("Real Hermes YouTube extracted opus fixture is stored in ignored tests/assets/ and is unavailable.")
    settings.MEDIA_ROOT = tmp_path / "media-root"

    post = import_obsidian_note_to_post(
        HERMES_YOUTUBE_PODCAST_NOTE,
        assets_dir=HERMES_YOUTUBE_ASSET_DIR,
        slug="hermes-six-features-podcast",
    )

    assert post.content_type == Post.ContentType.PODCAST
    assert post.media_url == ""
    assert post.primary_media is not None
    assert post.primary_media.original_filename == "hermes-six-features.opus"
    assert post.primary_media.media_type == PostMedia.MediaType.AUDIO
    assert post.primary_media.file.size == HERMES_YOUTUBE_AUDIO.stat().st_size
    assert post.cover_media is not None

    response = client.get(post.get_absolute_url())
    page = page_soup(response)
    player = page.select_one("audio.post-media-player")
    assert response.status_code == 200
    assert player is not None
    assert len(page.select("audio")) == 1
    assert page.select_one(".markdown-content audio") is None
    assert player["src"].endswith("/media/posts/hermes-six-features-podcast/hermes-six-features.opus")
    assert [button["data-seek-seconds"] for button in page.select("button.timecode-button")] == [
        "0", "76", "177", "296", "375", "458", "528"
    ]
