from pathlib import Path

import pytest
from django.core.files.storage import default_storage

from blog.models import Category, Post, PostMedia, Tag, build_file_slug
from blog.services.obsidian_importer import import_obsidian_note_to_post
from blog.slug_utils import build_slug


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Токены, параметры и встраивания", "tokeny-parametry-i-vstraivaniya"),
        ("Как нейросети превращают слова в геометрию", "kak-neyroseti-prevrashchayut-slova-v-geometriyu"),
        ("LM Studio: токены, параметры и встраивания 🧠", "lm-studio-tokeny-parametry-i-vstraivaniya"),
    ],
)
def test_build_slug_transliterates_cyrillic_readably(source, expected):
    assert build_slug(source) == expected


def test_media_filename_slug_transliterates_cyrillic():
    assert (
        build_file_slug("01_Как_нейросети_превращают_слова_в_геометрию.opus")
        == "01-kak-neyroseti-prevrashchayut-slova-v-geometriyu.opus"
    )


@pytest.mark.django_db
def test_post_category_and_tag_auto_slugs_are_unique_for_cyrillic():
    first_post = Post.objects.create(title="Токены, параметры и встраивания", content="Текст")
    second_post = Post.objects.create(title="Токены, параметры и встраивания", content="Другой текст")
    category = Category.objects.create(name="Локальные модели")
    tag = Tag.objects.create(name="Нейросети")

    assert first_post.slug == "tokeny-parametry-i-vstraivaniya"
    assert second_post.slug == "tokeny-parametry-i-vstraivaniya-2"
    assert category.slug == "lokalnye-modeli"
    assert tag.slug == "neyroseti"


@pytest.mark.django_db
def test_obsidian_import_auto_slug_and_media_for_lm_studio_like_article(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    assets_dir = tmp_path / "lm-studio-lesson-01"
    assets_dir.mkdir()
    (assets_dir / "cover-01.webp").write_bytes(b"RIFFxxxxWEBP")
    (assets_dir / "01_Как_нейросети_превращают_слова_в_геометрию.opus").write_bytes(b"OggS")
    note_path = assets_dir / "01-токены-параметры-и-встраивания.md"
    note_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Токены, параметры и встраивания"',
                "status: done",
                "---",
                "# Токены, параметры и встраивания 🧠",
                "![[cover-01.webp]]",
                "### 🎧 Подкаст",
                "![[01_Как_нейросети_превращают_слова_в_геометрию.opus]]",
            ]
        ),
        encoding="utf-8",
    )

    post = import_obsidian_note_to_post(note_path, assets_dir=assets_dir)

    assert post.slug == "tokeny-parametry-i-vstraivaniya"
    assert post.cover_media is not None
    assert post.media_files.filter(media_type=PostMedia.MediaType.IMAGE).count() == 1
    assert post.media_files.filter(media_type=PostMedia.MediaType.AUDIO).count() == 1
    assert "cover-01.webp" in post.content_html
    assert "01-kak-neyroseti-prevrashchayut-slova-v-geometriyu.opus" in post.content_html

    for media in post.media_files.all():
        default_storage.delete(media.file.name)
