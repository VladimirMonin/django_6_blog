"""Tests for the publisher CLI package — parser, client, and E2E CLI."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from django.test import Client

from api.models import ApiKey
from publisher.client import ApiError, publish_post
from publisher.parser import (
    extract_timecode_blocks,
    normalize_content_type,
    parse_markdown_file,
    parse_tags,
    split_frontmatter,
    time_to_seconds,
)


# ── Parser unit tests ────────────────────────────────────────────────────────


class TestSplitFrontmatter:
    def test_no_frontmatter(self):
        meta, body = split_frontmatter("Just text.")
        assert meta == {}
        assert body == "Just text."

    def test_simple_frontmatter(self):
        text = "---\ntitle: Hello\ndescription: World\n---\nBody here."
        meta, body = split_frontmatter(text)
        assert meta["title"] == "Hello"
        assert meta["description"] == "World"
        assert body == "Body here."

    def test_quoted_values(self):
        text = '---\ntitle: "Quoted"\n---\nBody.'
        meta, body = split_frontmatter(text)
        assert meta["title"] == "Quoted"


class TestTimeToSeconds:
    def test_mmss(self):
        assert time_to_seconds("1:30") == 90

    def test_hmmss(self):
        assert time_to_seconds("1:02:03") == 3723

    def test_zero(self):
        assert time_to_seconds("0:00") == 0


class TestExtractTimecodes:
    def test_simple_block(self):
        md = "Intro\n\n```timecodes\n0:00 Start\n1:30 Demo\n```\n\nEnd."
        body, tcs = extract_timecode_blocks(md)
        assert len(tcs) == 2
        assert tcs[0]["time"] == "0:00"
        assert tcs[0]["seconds"] == 0
        assert tcs[0]["label"] == "Start"
        assert tcs[1]["time"] == "1:30"
        assert tcs[1]["seconds"] == 90
        assert tcs[1]["label"] == "Demo"
        assert "```timecodes" not in body

    def test_no_block(self):
        body, tcs = extract_timecode_blocks("Just text.")
        assert tcs == []
        assert body == "Just text."

    def test_hmmss_format(self):
        md = "```timecodes\n1:00:00 One hour\n```"
        _, tcs = extract_timecode_blocks(md)
        assert tcs[0]["seconds"] == 3600


class TestNormalizeContentType:
    def test_english(self):
        assert normalize_content_type("article") == "article"
        assert normalize_content_type("video") == "video"

    def test_russian(self):
        assert normalize_content_type("видео") == "video"
        assert normalize_content_type("подкаст") == "podcast"

    def test_aliases(self):
        assert normalize_content_type("post") == "article"
        assert normalize_content_type("lesson") == "article"

    def test_invalid_defaults_to_article(self):
        assert normalize_content_type("nonexistent") == "article"

    def test_none_defaults_to_article(self):
        assert normalize_content_type(None) == "article"


class TestParseTags:
    def test_comma_separated(self):
        assert parse_tags("Python, Django, E2E") == ["Python", "Django", "E2E"]

    def test_list_format(self):
        tags = parse_tags("[Python, Django]")
        assert "Python" in tags
        assert "Django" in tags

    def test_empty(self):
        assert parse_tags("") == []

    def test_with_hash(self):
        tags = parse_tags("#python, #django")
        assert "Python" in tags
        assert "Django" in tags

    def test_acronyms(self):
        tags = parse_tags("ai, api, llm")
        assert "AI" in tags
        assert "API" in tags
        assert "LLM" in tags

    def test_kebab_to_humanized(self):
        tags = parse_tags("lm-studio")
        assert "LM Studio" in tags


class TestParseMarkdownFile:
    def test_full_frontmatter(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\n"
            "title: Test Post\n"
            "description: A test\n"
            "content_type: video\n"
            "media_url: https://example.com/v.mp4\n"
            "tags: Python, Django\n"
            "series: testing\n"
            "status: published\n"
            "---\n"
            "# Test Post\n\n"
            "Body text.\n\n"
            "```timecodes\n0:00 Intro\n2:57 Demo\n```\n",
            encoding="utf-8",
        )
        payload = parse_markdown_file(note)
        assert payload["title"] == "Test Post"
        assert payload["description"] == "A test"
        assert payload["content_type"] == "video"
        assert payload["media_url"] == "https://example.com/v.mp4"
        assert payload["status"] == "published"
        assert "Python" in payload["tags"]
        assert "Django" in payload["tags"]
        assert payload["category"] == "Testing"
        assert len(payload["timecodes"]) == 2
        assert payload["timecodes"][0] == {"time": "0:00", "label": "Intro"}
        assert payload["timecodes"][1] == {"time": "2:57", "label": "Demo"}
        # H1 duplicate should be removed from body
        assert "# Test Post" not in payload["content"]
        assert "Body text." in payload["content"]

    def test_draft_status(self, tmp_path):
        note = tmp_path / "draft.md"
        note.write_text(
            "---\ndescription: Draft\nstatus: draft\n---\nDraft body.\n",
            encoding="utf-8",
        )
        payload = parse_markdown_file(note)
        assert payload["status"] == "draft"

    def test_title_from_h1(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ndescription: Test\n---\n# My Heading\n\nBody.\n",
            encoding="utf-8",
        )
        payload = parse_markdown_file(note)
        assert payload["title"] == "My Heading"
        assert "# My Heading" not in payload["content"]

    def test_title_from_filename(self, tmp_path):
        note = tmp_path / "My Article.md"
        note.write_text("---\ndescription: Test\n---\nBody.\n", encoding="utf-8")
        payload = parse_markdown_file(note)
        assert payload["title"] == "My Article"

    def test_missing_description_raises(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("# Title\n\nBody.", encoding="utf-8")
        with pytest.raises(ValueError, match="description"):
            parse_markdown_file(note)

    def test_cli_overrides_frontmatter(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ntitle: FM Title\ndescription: FM Desc\n---\nBody.\n",
            encoding="utf-8",
        )
        payload = parse_markdown_file(
            note,
            title="CLI Title",
            description="CLI Desc",
            content_type="audio",
            media_url="https://example.com/a.mp3",
            status="draft",
            slug="custom-slug",
        )
        assert payload["title"] == "CLI Title"
        assert payload["description"] == "CLI Desc"
        assert payload["content_type"] == "audio"
        assert payload["media_url"] == "https://example.com/a.mp3"
        assert payload["status"] == "draft"
        assert payload["slug"] == "custom-slug"

    def test_obsidian_wikilinks_normalized(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ndescription: Test\n---\nLink to [[note-2|alias]].\n",
            encoding="utf-8",
        )
        payload = parse_markdown_file(note)
        assert "[[note-2|alias]]" not in payload["content"]
        assert "alias" in payload["content"]

    def test_russian_content_type(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ndescription: Test\ntype: подкаст\n---\nBody.\n",
            encoding="utf-8",
        )
        payload = parse_markdown_file(note)
        assert payload["content_type"] == "podcast"

    def test_no_timecodes_no_key(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("---\ndescription: Test\n---\nBody.\n", encoding="utf-8")
        payload = parse_markdown_file(note)
        assert "timecodes" not in payload

    def test_no_tags_no_key(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("---\ndescription: Test\n---\nBody.\n", encoding="utf-8")
        payload = parse_markdown_file(note)
        assert "tags" not in payload


# ── CLI dry-run tests ─────────────────────────────────────────────────────────


class TestCLIDryRun:
    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "publisher", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_dry_run_prints_payload(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ntitle: CLI Test\ndescription: Dry run\n---\nBody text.\n",
            encoding="utf-8",
        )
        result = self._run_cli("publish", str(note), "--dry-run")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["title"] == "CLI Test"
        assert payload["description"] == "Dry run"
        assert payload["content"] == "Body text."

    def test_dry_run_with_overrides(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ntitle: FM\ndescription: FM\n---\nBody.\n",
            encoding="utf-8",
        )
        result = self._run_cli(
            "publish", str(note), "--dry-run",
            "--title", "Override",
            "--content-type", "video",
            "--media-url", "https://example.com/v.mp4",
            "--status", "draft",
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["title"] == "Override"
        assert payload["content_type"] == "video"
        assert payload["media_url"] == "https://example.com/v.mp4"
        assert payload["status"] == "draft"

    def test_dry_run_with_timecodes(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text(
            "---\ndescription: TC test\n---\n"
            "Body.\n\n```timecodes\n0:00 Start\n1:30 End\n```\n",
            encoding="utf-8",
        )
        result = self._run_cli("publish", str(note), "--dry-run")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert len(payload["timecodes"]) == 2
        assert payload["timecodes"][0]["label"] == "Start"

    def test_missing_file_returns_error(self):
        result = self._run_cli("publish", "/nonexistent/file.md", "--dry-run")
        assert result.returncode == 1
        assert "not found" in result.stderr

    def test_missing_url_returns_error(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("---\ndescription: Test\n---\nBody.\n", encoding="utf-8")
        result = self._run_cli("publish", str(note))
        assert result.returncode == 1
        assert "url" in result.stderr.casefold()


# ── E2E: CLI → live server → public site ─────────────────────────────────────
# These tests use pytest-django's live_server fixture to run a real HTTP
# server, so urllib-based publish_post() can connect and the full agent
# workflow (CLI parser → HTTP POST → DB → public render) is verified.


@pytest.mark.django_db
def test_e2e_cli_publishes_article_and_post_appears_on_site(tmp_path, live_server):
    """Full cycle: CLI publishes a note → post visible on public list and detail."""
    from blog.models import Post

    key = ApiKey.objects.create(name="CLI Test Agent")
    note = tmp_path / "article.md"
    note.write_text(
        "---\n"
        "title: CLI E2E Article\n"
        "description: Published via CLI\n"
        "tags: Python, E2E\n"
        "series: testing\n"
        "---\n"
        "# CLI E2E Article\n\n"
        "This was published by the CLI tool.\n",
        encoding="utf-8",
    )
    payload = parse_markdown_file(note)
    result = publish_post(
        url=live_server.url,
        api_key=key.token,
        payload=payload,
    )
    assert result["title"] == "CLI E2E Article"
    assert result["status"] == "published"

    # Verify on public site
    client = Client()
    slug = result["slug"]
    detail = client.get(f"/post/{slug}/")
    assert detail.status_code == 200
    assert b"CLI E2E Article" in detail.content

    list_resp = client.get("/")
    assert list_resp.status_code == 200
    assert b"CLI E2E Article" in list_resp.content

    # Verify DB state
    post = Post.objects.get(slug=slug)
    assert post.content_type == "article"
    assert post.status == "published"
    assert post.category.name == "Testing"
    tag_names = set(post.tags.values_list("name", flat=True))
    assert "Python" in tag_names
    assert "E2E" in tag_names


@pytest.mark.django_db
def test_e2e_cli_publishes_video_with_timecodes(tmp_path, live_server):
    """CLI publishes a video post with timecodes via API."""
    from blog.models import Post

    key = ApiKey.objects.create(name="CLI Test Agent")
    note = tmp_path / "video.md"
    note.write_text(
        "---\n"
        "title: CLI E2E Video\n"
        "description: Video via CLI\n"
        "content_type: video\n"
        "media_url: https://example.com/v.mp4\n"
        "---\n"
        "# CLI E2E Video\n\n"
        "Video body.\n\n"
        "```timecodes\n0:00 Intro\n2:57 Demo\n10:00 End\n```\n",
        encoding="utf-8",
    )
    payload = parse_markdown_file(note)
    result = publish_post(
        url=live_server.url,
        api_key=key.token,
        payload=payload,
    )
    assert result["content_type"] == "video"
    assert result["media_url"] == "https://example.com/v.mp4"

    post = Post.objects.get(slug=result["slug"])
    assert len(post.timecodes) == 3
    assert post.timecodes[0]["label"] == "Intro"
    assert post.timecodes[1]["seconds"] == 177  # 2:57
    assert post.timecodes[2]["seconds"] == 600  # 10:00

    # Detail renders
    client = Client()
    detail = client.get(f"/post/{post.slug}/")
    assert detail.status_code == 200


@pytest.mark.django_db
def test_e2e_cli_publishes_draft_hidden_from_public(tmp_path, live_server):
    """CLI publishes a draft → not visible on public site."""
    from blog.models import Post

    key = ApiKey.objects.create(name="CLI Test Agent")
    note = tmp_path / "draft.md"
    note.write_text(
        "---\n"
        "title: CLI Draft\n"
        "description: Draft via CLI\n"
        "status: draft\n"
        "---\n"
        "Draft body.\n",
        encoding="utf-8",
    )
    payload = parse_markdown_file(note)
    result = publish_post(
        url=live_server.url,
        api_key=key.token,
        payload=payload,
    )
    assert result["status"] == "draft"

    post = Post.objects.get(slug=result["slug"])
    assert post.status == "draft"

    client = Client()
    detail = client.get(f"/post/{post.slug}/")
    assert detail.status_code == 404

    list_resp = client.get("/")
    assert b"CLI Draft" not in list_resp.content


@pytest.mark.django_db
def test_e2e_cli_replace_flag_overwrites_post(tmp_path, live_server):
    """CLI replace flag re-creates the post with updated content."""
    from blog.models import Post

    key = ApiKey.objects.create(name="CLI Test Agent")
    note = tmp_path / "replace.md"
    note.write_text(
        "---\n"
        "title: CLI Replace\n"
        "description: v1\n"
        "---\n"
        "v1 content.\n",
        encoding="utf-8",
    )
    payload = parse_markdown_file(note)
    r1 = publish_post(url=live_server.url, api_key=key.token, payload=payload)
    slug = r1["slug"]

    # Without replace → 409
    note.write_text(
        "---\n"
        "title: CLI Replace\n"
        "description: v2\n"
        "---\n"
        "v2 content.\n",
        encoding="utf-8",
    )
    payload2 = parse_markdown_file(note)
    with pytest.raises(ApiError) as exc_info:
        publish_post(url=live_server.url, api_key=key.token, payload=payload2)
    assert exc_info.value.status_code == 409

    # Replace with v2
    r3 = publish_post(
        url=live_server.url, api_key=key.token, payload=payload2, replace=True,
    )
    assert r3["description"] == "v2"

    # Old content gone
    post = Post.objects.get(slug=slug)
    assert post.description == "v2"
    assert "v1 content" not in post.content


@pytest.mark.django_db
def test_e2e_cli_all_four_content_types(tmp_path, live_server):
    """CLI publishes all 4 content types successfully."""
    from blog.models import Post

    key = ApiKey.objects.create(name="CLI Test Agent")

    types = {
        "article": "---\ndescription: A\n---\nArticle body.\n",
        "video": "---\ndescription: V\ncontent_type: video\nmedia_url: https://e.com/v.mp4\n---\nVideo body.\n",
        "audio": "---\ndescription: A\ncontent_type: audio\nmedia_url: https://e.com/a.mp3\n---\nAudio body.\n",
        "podcast": "---\ndescription: P\ncontent_type: podcast\nmedia_url: https://e.com/p.opus\n---\nPodcast body.\n",
    }

    for ctype, content in types.items():
        note = tmp_path / f"{ctype}.md"
        note.write_text(content, encoding="utf-8")
        payload = parse_markdown_file(note)
        result = publish_post(url=live_server.url, api_key=key.token, payload=payload)
        assert result["content_type"] == ctype, f"Mismatch for {ctype}"

        post = Post.objects.get(slug=result["slug"])
        assert post.content_type == ctype
        if ctype != "article":
            assert post.media_url != ""

        client = Client()
        detail = client.get(f"/post/{post.slug}/")
        assert detail.status_code == 200, f"Detail failed for {ctype}"


@pytest.mark.django_db
def test_e2e_cli_invalid_api_key_returns_error(tmp_path, live_server):
    """CLI with invalid API key gets a 401 error."""
    note = tmp_path / "note.md"
    note.write_text("---\ndescription: Test\n---\nBody.\n", encoding="utf-8")
    payload = parse_markdown_file(note)

    with pytest.raises(ApiError) as exc_info:
        publish_post(url=live_server.url, api_key="invalid-token", payload=payload)
    assert exc_info.value.status_code == 401


@pytest.mark.django_db
def test_e2e_cli_revoked_key_returns_401(tmp_path, live_server):
    """CLI with revoked API key gets 401."""
    key = ApiKey.objects.create(name="Revoked Agent")
    key.revoke()

    note = tmp_path / "note.md"
    note.write_text("---\ndescription: Test\n---\nBody.\n", encoding="utf-8")
    payload = parse_markdown_file(note)

    with pytest.raises(ApiError) as exc_info:
        publish_post(url=live_server.url, api_key=key.token, payload=payload)
    assert exc_info.value.status_code == 401