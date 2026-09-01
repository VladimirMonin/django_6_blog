"""Классифицировать заявленные User-Agent для локального наблюдения."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlerCandidate:
    """Заявленный провайдер и назначение User-Agent без проверки подлинности."""

    provider: str
    purpose: str


_CANDIDATE_TOKENS = (
    ("oai-searchbot", CrawlerCandidate("openai", "search")),
    ("gptbot", CrawlerCandidate("openai", "training")),
    ("chatgpt-user", CrawlerCandidate("openai", "user-fetch")),
    ("claude-searchbot", CrawlerCandidate("anthropic", "search")),
    ("claudebot", CrawlerCandidate("anthropic", "training")),
    ("claude-user", CrawlerCandidate("anthropic", "user-fetch")),
    ("perplexitybot", CrawlerCandidate("perplexity", "search")),
    ("perplexity-user", CrawlerCandidate("perplexity", "user-fetch")),
    ("google-extended", CrawlerCandidate("google", "training")),
    ("googlebot", CrawlerCandidate("google", "search")),
    ("bingbot", CrawlerCandidate("bing", "search")),
    ("bravebot", CrawlerCandidate("brave", "search")),
)


def classify_crawler_user_agent(user_agent: str) -> CrawlerCandidate | None:
    """Вернуть только кандидата, заявленного строкой User-Agent."""

    normalized_user_agent = user_agent.casefold()
    for token, candidate in _CANDIDATE_TOKENS:
        if token in normalized_user_agent:
            return candidate
    return None
