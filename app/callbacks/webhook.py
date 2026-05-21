import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_webhook(callback_url: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        httpx.post(callback_url, json=payload, timeout=settings.webhook_timeout_seconds)
    except httpx.HTTPError:
        logger.exception("Webhook callback failed: %s", callback_url)

