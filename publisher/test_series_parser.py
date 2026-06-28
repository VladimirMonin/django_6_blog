import pytest

from publisher.parser import parse_markdown_file


@pytest.mark.django_db
def test_parse_markdown_file_includes_series_and_order(tmp_path):
    note = tmp_path / "series-note.md"
    note.write_text(
        "---\n"
        "title: Series Note\n"
        "description: note desc\n"
        "category: Python\n"
        "series: Python Basics\n"
        "series_order: 2\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )

    payload = parse_markdown_file(note)
    assert payload["category"] == "Python"
    assert payload["series"] == "Python Basics"
    assert payload["series_order"] == 2
