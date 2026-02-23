"""Integration test: full notification pipeline without Celery.

Scenario
--------
1. Create a Slack channel config pointing at a local mock webhook server.
2. Create a notification rule for ``guardrail.triggered``.
3. Build a ``NotificationEvent`` (as if a guardrail fired).
4. Persist the event via ``NotificationDispatcher`` and skip actual Celery
   enqueueing — call ``NotificationEventProcessor.process()`` directly.
5. Assert:
   - Delivery record created with status SENT.
   - Mock webhook server received exactly 1 HTTP POST.

For a manual demo with real Slack/Telegram webhooks set the env vars:
    DEMO_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
    DEMO_TELEGRAM_WEBHOOK_URL=https://api.telegram.org/bot.../sendMessage?chat_id=...
and run:
    pytest tests/e2e/test_notifications_integration.py -v -s
"""

from __future__ import annotations

import os

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.services.notification_event_processor import (
    NotificationEventProcessor,
)
from src.domain.entities.notification_channel_config import (
    new_notification_channel_config,
)
from src.domain.entities.notification_rule import new_notification_rule
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)
from src.domain.value_objects.notification_delivery_status import (
    NotificationDeliveryStatus,
)
from src.domain.value_objects.notification_event import (
    NotificationEvent,
    make_notification_event_id,
)
from src.domain.value_objects.notification_event_type import (
    NotificationEventType,
)
from src.infra.adapters.channels.slack_webhook_channel import (
    SlackWebhookChannel,
)
from tests.e2e.mock_webhook_server import MockWebhookServer
from tests.fakes.notification_channel_configs_repository import (
    FakeNotificationChannelConfigsRepository,
)
from tests.fakes.notification_deliveries_repository import (
    FakeNotificationDeliveriesRepository,
)
from tests.fakes.notification_events_repository import (
    FakeNotificationEventsRepository,
)
from tests.fakes.notification_rate_limiter import FakeNotificationRateLimiter
from tests.fakes.notification_rules_repository import (
    FakeNotificationRulesRepository,
)


pytestmark = pytest.mark.asyncio


async def test_guardrail_notification_delivered_to_mock_webhook() -> None:
    """Full pipeline: guardrail.triggered → delivery record SENT + HTTP to mock."""
    async with MockWebhookServer() as server:
        events_repo = FakeNotificationEventsRepository()
        configs_repo = FakeNotificationChannelConfigsRepository()
        rules_repo = FakeNotificationRulesRepository()
        deliveries_repo = FakeNotificationDeliveriesRepository()

        # Channel config pointing at local mock server
        config = new_notification_channel_config(
            type=NotificationChannelType.SLACK,
            name="mock-slack",
            webhook_url=server.url,
        )
        await configs_repo.save(config)

        rule = new_notification_rule(
            event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
            channel_config_id=config.id,
        )
        await rules_repo.save(rule)

        # Build a notification event as the dispatcher would persist it
        entity_id = uuid4()
        now = datetime.now(UTC)
        event = NotificationEvent(
            event_id=make_notification_event_id(
                NotificationEventType.GUARDRAIL_TRIGGERED,
                entity_id,
                int(now.timestamp()),
            ),
            event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
            entity_type="experiment",
            entity_id=entity_id,
            payload={
                "experiment_name": "Homepage CTA Test",
                "flag_key": "homepage_cta",
                "owner_id": "analyst-1",
                "metric_key": "error_rate",
                "threshold": 0.05,
                "actual_value": 0.12,
                "action": "pause",
                "triggered_at": now.isoformat(),
            },
        )
        await events_repo.try_insert(event)

        processor = NotificationEventProcessor(
            events_repository=events_repo,
            rules_repository=rules_repo,
            channel_configs_repository=configs_repo,
            deliveries_repository=deliveries_repo,
            rate_limiter=FakeNotificationRateLimiter(),
            channel_registry={
                NotificationChannelType.SLACK: SlackWebhookChannel(),
            },
        )
        await processor.process(event.event_id)

        # Delivery marked SENT
        delivery = await deliveries_repo.get(event.event_id, rule.id)
        assert delivery is not None
        assert delivery.status == NotificationDeliveryStatus.SENT

        # Mock server received exactly 1 POST
        assert len(server.received_requests) == 1
        body = server.received_requests[0]["body"]
        assert "text" in body
        assert "error_rate" in body["text"]


async def test_experiment_lifecycle_notification_delivered_to_mock_webhook() -> (
    None
):
    """Full pipeline: experiment.launched → delivery record SENT + HTTP to mock."""
    async with MockWebhookServer() as server:
        events_repo = FakeNotificationEventsRepository()
        configs_repo = FakeNotificationChannelConfigsRepository()
        rules_repo = FakeNotificationRulesRepository()
        deliveries_repo = FakeNotificationDeliveriesRepository()

        config = new_notification_channel_config(
            type=NotificationChannelType.SLACK,
            name="mock-slack-launch",
            webhook_url=server.url,
        )
        await configs_repo.save(config)

        rule = new_notification_rule(
            event_type=NotificationEventType.EXPERIMENT_LAUNCHED,
            channel_config_id=config.id,
        )
        await rules_repo.save(rule)

        entity_id = uuid4()
        event = NotificationEvent(
            event_id=make_notification_event_id(
                NotificationEventType.EXPERIMENT_LAUNCHED, entity_id, 1
            ),
            event_type=NotificationEventType.EXPERIMENT_LAUNCHED,
            entity_type="experiment",
            entity_id=entity_id,
            payload={
                "experiment_name": "Checkout Flow v2",
                "flag_key": "checkout_v2",
                "owner_id": "pm-1",
                "status": "running",
                "version": 1,
            },
        )
        await events_repo.try_insert(event)

        processor = NotificationEventProcessor(
            events_repository=events_repo,
            rules_repository=rules_repo,
            channel_configs_repository=configs_repo,
            deliveries_repository=deliveries_repo,
            rate_limiter=FakeNotificationRateLimiter(),
            channel_registry={
                NotificationChannelType.SLACK: SlackWebhookChannel(),
            },
        )
        await processor.process(event.event_id)

        delivery = await deliveries_repo.get(event.event_id, rule.id)
        assert delivery is not None
        assert delivery.status == NotificationDeliveryStatus.SENT

        assert len(server.received_requests) == 1
        body = server.received_requests[0]["body"]
        assert "Checkout Flow v2" in body["text"]


async def test_rate_limited_second_dispatch_skipped() -> None:
    """Second dispatch within rate-limit window creates SKIPPED delivery, no HTTP call."""
    async with MockWebhookServer() as server:
        events_repo = FakeNotificationEventsRepository()
        configs_repo = FakeNotificationChannelConfigsRepository()
        rules_repo = FakeNotificationRulesRepository()
        deliveries_repo = FakeNotificationDeliveriesRepository()

        config = new_notification_channel_config(
            type=NotificationChannelType.SLACK,
            name="rl-test",
            webhook_url=server.url,
        )
        await configs_repo.save(config)

        rule = new_notification_rule(
            event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
            channel_config_id=config.id,
            rate_limit_seconds=3600,
        )
        await rules_repo.save(rule)

        rate_limiter = FakeNotificationRateLimiter()
        rate_limiter.block(rule.id, uuid4())  # any entity blocked

        entity_id = uuid4()
        event = NotificationEvent(
            event_id=make_notification_event_id(
                NotificationEventType.GUARDRAIL_TRIGGERED,
                entity_id,
                1,
            ),
            event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
            entity_type="experiment",
            entity_id=entity_id,
            payload={"metric_key": "err"},
        )
        await events_repo.try_insert(event)

        # Override the rate limiter to block this specific entity
        rate_limiter.block(rule.id, entity_id)

        processor = NotificationEventProcessor(
            events_repository=events_repo,
            rules_repository=rules_repo,
            channel_configs_repository=configs_repo,
            deliveries_repository=deliveries_repo,
            rate_limiter=rate_limiter,
            channel_registry={
                NotificationChannelType.SLACK: SlackWebhookChannel()
            },
        )
        await processor.process(event.event_id)

        assert len(server.received_requests) == 0
        delivery = await deliveries_repo.get(event.event_id, rule.id)
        assert delivery is not None
        assert (
            delivery.status == NotificationDeliveryStatus.SKIPPED_RATE_LIMITED
        )


# ---------------------------------------------------------------------------
# Optional: real webhook demo test
# Set env vars to run this against real Slack/Telegram
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("DEMO_SLACK_WEBHOOK_URL"),
    reason="Set DEMO_SLACK_WEBHOOK_URL to run demo against real Slack",
)
async def test_demo_real_slack_webhook() -> None:
    """Manual demo: sends a real Slack notification. Set DEMO_SLACK_WEBHOOK_URL in .env."""
    webhook_url = os.environ["DEMO_SLACK_WEBHOOK_URL"]

    events_repo = FakeNotificationEventsRepository()
    configs_repo = FakeNotificationChannelConfigsRepository()
    rules_repo = FakeNotificationRulesRepository()
    deliveries_repo = FakeNotificationDeliveriesRepository()

    config = new_notification_channel_config(
        type=NotificationChannelType.SLACK,
        name="real-slack",
        webhook_url=webhook_url,
    )
    await configs_repo.save(config)

    rule = new_notification_rule(
        event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
        channel_config_id=config.id,
    )
    await rules_repo.save(rule)

    entity_id = uuid4()
    now = datetime.now(UTC)
    event = NotificationEvent(
        event_id=make_notification_event_id(
            NotificationEventType.GUARDRAIL_TRIGGERED,
            entity_id,
            int(now.timestamp()),
        ),
        event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
        entity_type="experiment",
        entity_id=entity_id,
        payload={
            "experiment_name": "🧪 Demo Experiment",
            "flag_key": "demo_flag",
            "owner_id": "demo-user",
            "metric_key": "error_rate",
            "threshold": 0.05,
            "actual_value": 0.15,
            "action": "pause",
            "triggered_at": now.isoformat(),
        },
    )
    await events_repo.try_insert(event)

    processor = NotificationEventProcessor(
        events_repository=events_repo,
        rules_repository=rules_repo,
        channel_configs_repository=configs_repo,
        deliveries_repository=deliveries_repo,
        rate_limiter=FakeNotificationRateLimiter(),
        channel_registry={
            NotificationChannelType.SLACK: SlackWebhookChannel(),
        },
    )
    await processor.process(event.event_id)

    delivery = await deliveries_repo.get(event.event_id, rule.id)
    assert delivery is not None
    assert delivery.status == NotificationDeliveryStatus.SENT
    print(f"\n✅ Real Slack notification sent! Delivery id={delivery.id}")
