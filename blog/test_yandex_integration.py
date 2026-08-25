"""Yandex Webmaster and Metrika integration contract."""

import pytest

from django.test import Client


YANDEX_VERIFICATION_PATH = "/yandex_5834a95c038b9599.html"
YANDEX_VERIFICATION_BODY = """<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body>Verification: 5834a95c038b9599</body>
</html>
"""

pytestmark = pytest.mark.django_db


def test_yandex_webmaster_verification_document_is_exact():
    response = Client().get(YANDEX_VERIFICATION_PATH)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=UTF-8"
    assert response.content.decode() == YANDEX_VERIFICATION_BODY


def test_yandex_metrika_is_initialized_once_on_full_pages():
    client = Client()

    for path in ("/", "/about/"):
        response = client.get(path)
        assert response.status_code == 200
        body = response.content.decode()
        assert body.count("https://mc.yandex.ru/metrika/tag.js?id=111929557") == 1
        assert body.count("ym(111929557, 'init'") == 1
        assert "m[i]=m[i]||function()" in body
        assert "webvisor:true" in body
        assert "accurateTrackBounce:true" in body
        assert "trackLinks:true" in body
        assert body.count("https://mc.yandex.ru/watch/111929557") == 1


def test_htmx_fragment_does_not_repeat_metrika_bootstrap():
    response = Client().get("/", HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    body = response.content.decode()
    assert "mc.yandex.ru/metrika/tag.js" not in body
    assert "mc.yandex.ru/watch/111929557" not in body
