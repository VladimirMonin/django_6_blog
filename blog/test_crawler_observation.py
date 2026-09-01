"""Tests for local, unverified crawler-observation logging."""

import json
import logging
from unittest.mock import patch

import pytest
from django.conf import settings

from blog.crawler_observation import CrawlerCandidate, classify_crawler_user_agent
from config.settings import _JsonFormatter


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        ("GPTBot/1.0", CrawlerCandidate("openai", "training")),
        ("OAI-SearchBot/1.0", CrawlerCandidate("openai", "search")),
        ("ChatGPT-User/1.0", CrawlerCandidate("openai", "user-fetch")),
        ("ClaudeBot/1.0", CrawlerCandidate("anthropic", "training")),
        ("Claude-SearchBot/1.0", CrawlerCandidate("anthropic", "search")),
        ("Claude-User/1.0", CrawlerCandidate("anthropic", "user-fetch")),
        ("PerplexityBot/1.0", CrawlerCandidate("perplexity", "search")),
        ("Perplexity-User/1.0", CrawlerCandidate("perplexity", "user-fetch")),
        ("Googlebot/2.1", CrawlerCandidate("google", "search")),
        ("Google-Extended", CrawlerCandidate("google", "training")),
        ("bingbot/2.0", CrawlerCandidate("bing", "search")),
        ("Bravebot", CrawlerCandidate("brave", "search")),
    ],
)
def test_classifies_supported_crawler_candidates(user_agent, expected):
    """Known declared User-Agent tokens are candidates, never verified crawlers."""

    assert classify_crawler_user_agent(user_agent) == expected


def test_ignores_non_candidate_user_agents():
    """Ordinary or ambiguous user agents do not create an observation candidate."""

    assert classify_crawler_user_agent("Mozilla/5.0") is None
    assert classify_crawler_user_agent("") is None


@pytest.mark.django_db
def test_logs_one_query_free_record_after_candidate_public_response(client):
    """A candidate response emits one privacy-bounded record after the response exists."""

    with patch("blog.middleware.logger.info") as info:
        response = client.get(
            "/?token=do-not-log",
            HTTP_USER_AGENT="OAI-SearchBot/1.0",
            REMOTE_ADDR="198.51.100.42",
            HTTP_COOKIE="sessionid=do-not-log",
            HTTP_AUTHORIZATION="Bearer do-not-log",
        )

    assert response.status_code == 200
    info.assert_called_once()
    assert info.call_args.args == ("crawler_observation",)
    record = info.call_args.kwargs["extra"]
    assert set(record) == {
        "provider",
        "purpose",
        "remote_ip",
        "method",
        "path",
        "status",
        "elapsed_ms",
        "user_agent",
        "verified_identity",
    }
    assert record == {
        "provider": "openai",
        "purpose": "search",
        "remote_ip": "198.51.100.42",
        "method": "GET",
        "path": "/",
        "status": 200,
        "elapsed_ms": record["elapsed_ms"],
        "user_agent": "OAI-SearchBot/1.0",
        "verified_identity": False,
    }
    assert isinstance(record["elapsed_ms"], int)
    assert record["elapsed_ms"] >= 0
    assert "token=do-not-log" not in str(record)
    assert "sessionid=do-not-log" not in str(record)
    assert "Bearer do-not-log" not in str(record)


@pytest.mark.django_db
@pytest.mark.parametrize(("path", "status"), [("/", 200), ("/admin/", 302)])
def test_logs_candidate_public_and_admin_paths(client, path, status):
    """Observation is response-only and has no public-path allowlist."""

    with patch("blog.middleware.logger.info") as info:
        response = client.get(path, HTTP_USER_AGENT="Googlebot/2.1")

    assert response.status_code == status
    info.assert_called_once()
    record = info.call_args.kwargs["extra"]
    assert record["path"] == path
    assert record["status"] == status


@pytest.mark.django_db
def test_does_not_log_non_candidates(client):
    """A normal browser request remains silent for crawler observation."""

    with patch("blog.middleware.logger.info") as info:
        response = client.get("/", HTTP_USER_AGENT="Mozilla/5.0")

    assert response.status_code == 200
    info.assert_not_called()


@pytest.mark.django_db
def test_logging_failure_does_not_change_candidate_response(client):
    """A logging error is fail-open and cannot replace the application response."""

    with patch("blog.middleware.logger.info", side_effect=RuntimeError("logger unavailable")):
        response = client.get("/?source=search", HTTP_USER_AGENT="Bravebot/1.0")

    assert response.status_code == 200


def test_crawler_logger_uses_existing_json_console_handler():
    """Crawler observation is formatted as one JSON log line without new handlers."""

    assert settings.LOGGING["loggers"]["crawler_observation"] == {
        "handlers": ["console_json"],
        "level": "INFO",
        "propagate": False,
    }


def test_crawler_log_fields_serialize_as_one_json_record():
    """The configured formatter preserves the bounded observation fields as JSON."""

    record = logging.makeLogRecord(
        {
            "name": "crawler_observation",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "crawler_observation",
            "args": (),
            "provider": "openai",
            "purpose": "search",
            "remote_ip": "198.51.100.42",
            "method": "GET",
            "path": "/",
            "status": 200,
            "elapsed_ms": 12,
            "user_agent": "OAI-SearchBot/1.0",
            "verified_identity": False,
        }
    )

    payload = json.loads(_JsonFormatter().format(record))

    assert payload["logger"] == "crawler_observation"
    assert payload["message"] == "crawler_observation"
    assert payload["provider"] == "openai"
    assert payload["purpose"] == "search"
    assert payload["remote_ip"] == "198.51.100.42"
    assert payload["method"] == "GET"
    assert payload["path"] == "/"
    assert payload["status"] == 200
    assert payload["elapsed_ms"] == 12
    assert payload["user_agent"] == "OAI-SearchBot/1.0"
    assert payload["verified_identity"] is False
