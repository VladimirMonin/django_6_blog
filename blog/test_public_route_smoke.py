import pytest

from blog.models import Post


pytestmark = pytest.mark.django_db


def assert_empty_homepage_renders_safely(response):
    assert response.status_code == 200
    assert Post.objects.count() == 0

    body = response.content.decode()
    assert "Постов не найдено." in body
    assert "blog-search-button" in body
    assert 'type="submit"' in body
    assert "Последние посты" in body


def test_homepage_returns_200_with_empty_state_on_empty_database(client):
    response = client.get("/")

    assert_empty_homepage_renders_safely(response)


def test_about_page_returns_200_and_renders_about_content(client):
    response = client.get("/about/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "О проекте" in body
    assert "Django 6 Blog" in body


def test_admin_login_returns_200_with_test_client_host(client):
    response = client.get("/admin/login/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "username" in body
    assert "password" in body


def test_high_page_query_on_empty_homepage_falls_back_safely(client):
    response = client.get("/", {"page": "999"})

    assert_empty_homepage_renders_safely(response)
