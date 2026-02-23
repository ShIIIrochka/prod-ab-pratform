"""Slack channel adapter via incoming webhooks."""

from __future__ import annotations

import logging

import httpx

from src.application.ports.notification_channel import NotificationChannelPort


logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


class SlackWebhookChannel(NotificationChannelPort):
    """Sends messages to a Slack channel via Incoming Webhook URL."""

    async def send(self, message: str, webhook_url: str) -> None:
        payload = {"text": message}
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(
                "Slack notification sent to webhook (status=%d)",
                response.status_code,
            )
