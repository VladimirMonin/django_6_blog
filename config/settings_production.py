"""Fail-closed production settings.

This module is importable offline. It validates configuration without opening
network connections; connectivity is owned by readiness checks and deployment.
"""

from urllib.parse import urlparse

import dj_database_url

from config.env import env, env_bool, env_int, env_list, env_required
from config.settings import *  # noqa: F403


_debug_value = env_required("DJANGO_DEBUG").lower()
if _debug_value != "false":
    raise RuntimeError("Production requires DJANGO_DEBUG=false")
DEBUG = False

SECRET_KEY = env_required("DJANGO_SECRET_KEY")
if SECRET_KEY.startswith("django-insecure-") or len(SECRET_KEY) < 50:
    raise RuntimeError("DJANGO_SECRET_KEY is a placeholder or too short")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must contain explicit hosts")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS or any(
    parsed.scheme != "https"
    or not parsed.hostname
    or parsed.username is not None
    or parsed.password is not None
    or parsed.path not in {"", "/"}
    or parsed.params
    or parsed.query
    or parsed.fragment
    for origin in CSRF_TRUSTED_ORIGINS
    if (parsed := urlparse(origin))
):
    raise RuntimeError("DJANGO_CSRF_TRUSTED_ORIGINS must contain valid HTTPS origins")

DATABASE_URL = env_required("DATABASE_URL")
_database_url = urlparse(DATABASE_URL)
if (
    _database_url.scheme not in {"postgres", "postgresql"}
    or not _database_url.hostname
    or not _database_url.path.strip("/")
):
    raise RuntimeError("Production DATABASE_URL must use PostgreSQL")
DATABASES = {  # noqa: F405
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
        conn_health_checks=True,
    )
}
DATABASES["default"].setdefault("OPTIONS", {}).update(
    {
        "connect_timeout": 2,
        "options": "-c statement_timeout=2000",
    }
)

if env_required("DJANGO_MEDIA_STORAGE") != "s3":
    raise RuntimeError("Production DJANGO_MEDIA_STORAGE must be s3")

_s3_required = {
    name: env_required(name)
    for name in (
        "MEDIA_S3_ENDPOINT_URL",
        "MEDIA_S3_BUCKET_NAME",
        "MEDIA_S3_REGION_NAME",
        "MEDIA_S3_AUTH_ID",
        "MEDIA_S3_AUTH_MATERIAL",
    )
}
_s3_custom_domain = env("MEDIA_S3_CUSTOM_DOMAIN").strip() or None
_s3_signed_urls = env_bool("MEDIA_S3_SIGNED_URLS", False)
if _s3_custom_domain and (
    "://" in _s3_custom_domain
    or "/" in _s3_custom_domain
    or _s3_custom_domain.startswith(".")
):
    raise RuntimeError("MEDIA_S3_CUSTOM_DOMAIN must be a hostname without scheme or path")
if _s3_custom_domain and _s3_signed_urls:
    raise RuntimeError("Private signed S3 URLs require MEDIA_S3_CUSTOM_DOMAIN to be empty")
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "endpoint_url": _s3_required["MEDIA_S3_ENDPOINT_URL"],
            "bucket_name": _s3_required["MEDIA_S3_BUCKET_NAME"],
            "region_name": _s3_required["MEDIA_S3_REGION_NAME"],
            "access_key": _s3_required["MEDIA_S3_AUTH_ID"],
            "secret_key": _s3_required["MEDIA_S3_AUTH_MATERIAL"],
            "custom_domain": _s3_custom_domain,
            "querystring_auth": _s3_signed_urls,
            "querystring_expire": env_int("MEDIA_S3_SIGNED_URL_TTL_SECONDS", 3600),
            "object_parameters": {
                "CacheControl": env("MEDIA_S3_CACHE_CONTROL", "public,max-age=86400")
            },
            "file_overwrite": env_bool("MEDIA_S3_FILE_OVERWRITE", False),
            "addressing_style": env("MEDIA_S3_ADDRESSING_STYLE", "path"),
            "signature_version": env("MEDIA_S3_SIGNATURE_VERSION", "s3v4"),
            "verify": env_bool("MEDIA_S3_VERIFY_SSL", True),
        },
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# HSTS is intentionally enabled only after a separately approved live TLS check.
SECURE_HSTS_SECONDS = 0
SILENCED_SYSTEM_CHECKS = ["security.W004"]
