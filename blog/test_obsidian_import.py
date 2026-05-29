"""Smoke tests for importing a real copied Obsidian lesson fixture."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from blog.models import Post
from blog.services.obsidian_importer import import_obsidian_note_to_post

FIXTURE_DIR = Path("tests/assets/obsidian/lm-studio-lesson-01")
FIXTURE_NOTE = FIXTURE_DIR / "01-токены-параметры-и-встраивания.md"


@pytest.mark.django_db
def test_real_obsidian_lm_studio_lesson_import_renders_media_and_mermaid(client):
    if not FIXTURE_NOTE.exists():
        pytest.skip("local Obsidian LM Studio fixture is absent; copy it into tests/assets/ first")

    post = import_obsidian_note_to_post(
        FIXTURE_NOTE,
        assets_dir=FIXTURE_DIR,
        slug="lm-studio-lesson-01-test",
    )

    response = client.get(post.get_absolute_url())
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    assert post.title == "Токены, параметры и встраивания"
    assert post.media_files.count() == 9
    assert len(soup.select("img[src]")) == 8
    assert len(soup.select("audio[src]")) == 1
    assert len(soup.select(".mermaid")) >= 1
    assert len(soup.select("blockquote.alert")) >= 1
    assert not soup.select('img[src$=".opus"]')
    assert "![[" not in post.content_html
    assert "[!" not in post.content_html

    for media in post.media_files.all():
        assert Path(media.file.path).exists()
