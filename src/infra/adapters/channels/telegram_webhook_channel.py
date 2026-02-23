"""Telegram channel adapter via outgoing webhook URL.

This uses a webhook endpoint that accepts a plain JSON POST with a 'text' field.
This follows the ТЗ requirement of using webhooks for delivery, as opposed to
Bot API polling.
"""

from __future__ import annotations

import logging

import httpx

from src.application.ports.notification_channel import NotificationChannelPort


logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


class TelegramWebhookChannel(NotificationChannelPort):
    """Sends messages to a Telegram chat via a configured webhook URL.

    The webhook_url should be a configured bot-API endpoint in the form:
    https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>
    """

    async def send(self, message: str, webhook_url: str) -> None:
        payload = {"text": message, "parse_mode": "Markdown"}
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(
                "Telegram notification sent to webhook (status=%d)",
                response.status_code,
            )
