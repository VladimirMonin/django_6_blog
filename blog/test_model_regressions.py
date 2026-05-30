import pytest

from blog.models import Category, Post, Tag


@pytest.mark.django_db
def test_post_english_title_auto_generates_non_empty_slug():
    post = Post.objects.create(title="Linux Smoke Test", content="Body")

    assert post.slug == "linux-smoke-test"


@pytest.mark.django_db
def test_post_russian_title_auto_generates_non_empty_transliterated_slug():
    post = Post.objects.create(title="Привет мир", content="Текст")

    assert post.slug == "privet-mir"


@pytest.mark.django_db
def test_category_and_tag_english_names_auto_generate_non_empty_slugs():
    category = Category.objects.create(name="Linux Notes")
    tag = Tag.objects.create(name="Smoke Test")

    assert category.slug == "linux-notes"
    assert tag.slug == "smoke-test"


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "0 просмотров"),
        (1, "1 просмотр"),
        (2, "2 просмотра"),
        (5, "5 просмотров"),
        (11, "11 просмотров"),
        (21, "21 просмотр"),
        (22, "22 просмотра"),
        (25, "25 просмотров"),
    ],
)
def test_view_count_label_uses_russian_plural_forms(count, expected):
    post = Post(title="Counters", content="Body", view_count=count)

    assert post.view_count_label == expected


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "0 лайков"),
        (1, "1 лайк"),
        (2, "2 лайка"),
        (5, "5 лайков"),
        (11, "11 лайков"),
        (21, "21 лайк"),
        (22, "22 лайка"),
        (25, "25 лайков"),
    ],
)
def test_like_count_label_uses_russian_plural_forms(count, expected):
    post = Post(title="Counters", content="Body", like_count=count)

    assert post.like_count_label == expected
