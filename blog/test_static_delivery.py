"""Offline static delivery contract tests."""

import json

from django.core.management import call_command
from django.test import override_settings


@override_settings(
    DEBUG=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
        },
    },
)
def test_collectstatic_uses_unique_absolute_root_and_manifest(tmp_path):
    target = tmp_path / "staticfiles"
    with override_settings(STATIC_ROOT=target):
        call_command("collectstatic", interactive=False, verbosity=0)
    manifest = target / "staticfiles.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["version"] == "1.1"
    assert data["paths"]
    assert any(path.startswith("admin/") for path in data["paths"])
    representatives = {
        "project": "css/style.css",
        "component": "post_card/post_card.css",
    }
    for kind, source in representatives.items():
        assert source in data["paths"], f"missing {kind} asset"
        assert data["paths"][source] != source
        assert (target / data["paths"][source]).exists()
    for prefix in ("admin/", "unfold/"):
        source = next(path for path in data["paths"] if path.startswith(prefix))
        assert data["paths"][source] != source
        assert (target / data["paths"][source]).exists()


@override_settings(DEBUG=False)
def test_django_does_not_serve_static_in_production(client):
    assert client.get("/static/css/style.css").status_code == 404


def test_nginx_example_never_falls_static_back_to_application():
    from pathlib import Path

    text = (
        Path(__file__).parents[1] / "deploy/nginx/django-6-blog.conf.example"
    ).read_text(encoding="utf-8")
    static_blocks = [block for block in text.split("location ") if block.startswith("/static/")]
    assert static_blocks
    assert all("try_files $uri =404" in block for block in static_blocks)
    assert all("proxy_pass" not in block for block in static_blocks)
