"""Неблокирующее локальное наблюдение за заявленными crawler User-Agent."""

import logging
import time

from .crawler_observation import classify_crawler_user_agent


logger = logging.getLogger("crawler_observation")


class CrawlerObservationMiddleware:
    """Логировать кандидатов после ответа, не изменяя его при сбое наблюдения."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        try:
            candidate = classify_crawler_user_agent(user_agent)
        except Exception:
            candidate = None

        started_at = time.monotonic()
        response = self.get_response(request)

        if candidate is not None:
            try:
                logger.info(
                    "crawler_observation",
                    extra={
                        "provider": candidate.provider,
                        "purpose": candidate.purpose,
                        "remote_ip": str(request.META.get("REMOTE_ADDR") or ""),
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
                        "user_agent": user_agent,
                        "verified_identity": False,
                    },
                )
            except Exception:
                pass

        return response
