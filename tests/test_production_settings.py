"""Offline tests for fail-closed production settings."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


BASE_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings_production",
    "DJANGO_DEBUG": "false",
    "DJANGO_SECRET_KEY": "test-only-production-key-with-sufficient-entropy-123456789-ABCDEFG",
    "DJANGO_ALLOWED_HOSTS": "example.test",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.test",
    "DATABASE_URL": "postgresql://user:pass@127.0.0.1:5432/blog",
    "DJANGO_MEDIA_STORAGE": "s3",
    "MEDIA_S3_ENDPOINT_URL": "https://s3.example.invalid",
    "MEDIA_S3_BUCKET_NAME": "bucket",
    "MEDIA_S3_REGION_NAME": "us-east-1",
    "MEDIA_S3_AUTH_ID": "test-id",
    "MEDIA_S3_AUTH_MATERIAL": "test-material",
    "MEDIA_S3_CUSTOM_DOMAIN": "media.example.test",
}


def run_settings(overrides=None, remove=()):
    env = os.environ.copy()
    env.update(BASE_ENV)
    env.update(overrides or {})
    for name in remove:
        env.pop(name, None)
    return subprocess.run(
        [sys.executable, "-c", "import config.settings_production"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize(
    ("overrides", "remove"),
    [
        ({"DJANGO_DEBUG": "true"}, ()),
        ({"DJANGO_DEBUG": "not-a-boolean"}, ()),
        ({"DJANGO_SECRET_KEY": "too-short"}, ()),
        ({"DJANGO_SECRET_KEY": "django-insecure-" + "x" * 60}, ()),
        ({"DJANGO_ALLOWED_HOSTS": "*"}, ()),
        ({"DJANGO_CSRF_TRUSTED_ORIGINS": "http://example.test"}, ()),
        ({"DJANGO_CSRF_TRUSTED_ORIGINS": "https://user@example.test"}, ()),
        ({"DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.test/path"}, ()),
        ({"DATABASE_URL": "sqlite:///db.sqlite3"}, ()),
        ({"DATABASE_URL": "postgresql:///blog"}, ()),
        ({"DJANGO_MEDIA_STORAGE": "filesystem"}, ()),
        ({}, ("DJANGO_DEBUG",)),
        ({}, ("DJANGO_SECRET_KEY",)),
        ({}, ("DJANGO_ALLOWED_HOSTS",)),
        ({}, ("DJANGO_CSRF_TRUSTED_ORIGINS",)),
        ({}, ("DATABASE_URL",)),
        ({}, ("DJANGO_MEDIA_STORAGE",)),
        ({}, ("MEDIA_S3_BUCKET_NAME",)),
    ],
)
def test_production_settings_fail_closed(overrides, remove):
    result = run_settings(overrides, remove)
    assert result.returncode != 0


def test_production_settings_import_without_network_access():
    result = run_settings()
    assert result.returncode == 0, result.stderr


def test_private_s3_bucket_does_not_require_custom_domain():
    result = run_settings(
        {"MEDIA_S3_SIGNED_URLS": "true"},
        remove=("MEDIA_S3_CUSTOM_DOMAIN",),
    )
    assert result.returncode == 0, result.stderr


def test_private_signed_s3_refuses_custom_domain_without_cdn_signing_contract():
    result = run_settings({"MEDIA_S3_SIGNED_URLS": "true"})
    assert result.returncode != 0
    assert "require MEDIA_S3_CUSTOM_DOMAIN to be empty" in result.stderr


@pytest.mark.parametrize(
    "custom_domain",
    ["https://media.example.test", "media.example.test/path", ".example.test"],
)
def test_s3_custom_domain_accepts_only_a_hostname(custom_domain):
    result = run_settings({"MEDIA_S3_CUSTOM_DOMAIN": custom_domain})
    assert result.returncode != 0


def test_optional_public_s3_custom_domain_is_passed_to_storage():
    script = """
from config import settings_production as s
options = s.STORAGES['default']['OPTIONS']
assert options['custom_domain'] == 'media.example.test'
assert options['querystring_auth'] is False
"""
    env = os.environ.copy()
    env.update(BASE_ENV)
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, text=True, capture_output=True, timeout=10
    )
    assert result.returncode == 0, result.stderr


def test_production_settings_preserve_static_alias_and_database_timeouts():
    script = """
import json
from config import settings_production as s
print(json.dumps({
    'static': s.STORAGES['staticfiles']['BACKEND'],
    'default': s.STORAGES['default']['BACKEND'],
    'options': s.DATABASES['default']['OPTIONS'],
}))
"""
    env = os.environ.copy()
    env.update(BASE_ENV)
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, text=True, capture_output=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert "ManifestStaticFilesStorage" in result.stdout
    assert "S3Storage" in result.stdout
    assert '"connect_timeout": 2' in result.stdout
    assert "statement_timeout=2000" in result.stdout


def test_local_settings_keep_sqlite_defaults():
    script = """
import json
from config import settings as s
print(json.dumps({
    'engine': s.DATABASES['default']['ENGINE'],
    'storage': s.STORAGES['default']['BACKEND'],
}))
"""
    env = os.environ.copy()
    for name in BASE_ENV:
        env.pop(name, None)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, text=True, capture_output=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert "django.db.backends.sqlite3" in result.stdout
    assert "django.core.files.storage.FileSystemStorage" in result.stdout
