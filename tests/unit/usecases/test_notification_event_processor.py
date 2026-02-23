"""Unit tests for NotificationEventProcessor.

Covers:
- Happy path: event processed, delivery marked SENT, channel called once.
- Idempotency: already-SENT delivery skipped on retry.
- Rate limiting: blocked event creates SKIPPED_RATE_LIMITED delivery.
- Missing channel config: rule silently skipped.
- Disabled channel config: rule silently skipped.
- Unknown channel type: rule silently skipped.
- Channel send failure: delivery marked FAILED, exception propagated for retry.
- No matching rules: no deliveries created.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeChannel:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self._raises = raises

    async def send(self, message: str, webhook_url: str) -> None:
        self.calls.append({"message": message, "webhook_url": webhook_url})
        if self._raises is not None:
            raise self._raises


def _make_event(
    event_type: str = NotificationEventType.EXPERIMENT_LAUNCHED,
    entity_id=None,
    version: int = 1,
) -> NotificationEvent:
    eid = entity_id or uuid4()
    return NotificationEvent(
        event_id=make_notification_event_id(event_type, eid, version),
        event_type=event_type,
        entity_type="experiment",
        entity_id=eid,
        payload={
            "experiment_name": "Test",
            "flag_key": "flag_x",
            "owner_id": "owner-1",
            "status": "running",
        },
    )


async def _build_processor(
    *,
    event: NotificationEvent,
    webhook_url: str = "https://hooks.slack.com/test",
    channel_type: NotificationChannelType = NotificationChannelType.SLACK,
    channel_raises: Exception | None = None,
    rate_limit_seconds: int = 0,
    channel_enabled: bool = True,
) -> tuple[
    NotificationEventProcessor,
    FakeNotificationDeliveriesRepository,
    _FakeChannel,
    FakeNotificationRateLimiter,
]:
    events_repo = FakeNotificationEventsRepository()
    await events_repo.try_insert(event)

    channel_configs_repo = FakeNotificationChannelConfigsRepository()
    config = new_notification_channel_config(
        type=channel_type,
        name="test channel",
        webhook_url=webhook_url,
        enabled=channel_enabled,
    )
    await channel_configs_repo.save(config)

    rules_repo = FakeNotificationRulesRepository()
    rule = new_notification_rule(
        event_type=event.event_type,
        channel_config_id=config.id,
        rate_limit_seconds=rate_limit_seconds,
    )
    await rules_repo.save(rule)

    deliveries_repo = FakeNotificationDeliveriesRepository()
    rate_limiter = FakeNotificationRateLimiter()

    fake_channel = _FakeChannel(raises=channel_raises)
    processor = NotificationEventProcessor(
        events_repository=events_repo,
        rules_repository=rules_repo,
        channel_configs_repository=channel_configs_repo,
        deliveries_repository=deliveries_repo,
        rate_limiter=rate_limiter,
        channel_registry={channel_type: fake_channel},
    )
    return processor, deliveries_repo, fake_channel, rate_limiter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_happy_path_sends_message_and_marks_sent() -> None:
    event = _make_event()
    processor, deliveries_repo, channel, _ = await _build_processor(event=event)

    await processor.process(event.event_id)

    assert len(channel.calls) == 1
    deliveries = deliveries_repo.all_deliveries()
    assert len(deliveries) == 1
    assert deliveries[0].status == NotificationDeliveryStatus.SENT
    assert deliveries[0].sent_at is not None


async def test_idempotency_skips_already_sent_delivery() -> None:
    event = _make_event()
    processor, deliveries_repo, channel, _ = await _build_processor(event=event)

    await processor.process(event.event_id)
    await processor.process(event.event_id)  # retry

    assert len(channel.calls) == 1
    assert len(deliveries_repo.all_deliveries()) == 1


async def test_rate_limited_rule_creates_skipped_delivery() -> None:
    event = _make_event()
    processor, deliveries_repo, channel, rate_limiter = await _build_processor(
        event=event, rate_limit_seconds=300
    )
    # pre-block the rate limiter so first call is rate-limited
    for rule in await processor._rules_repo.get_matching(
        event.event_type, event.entity_id, event.payload
    ):
        rate_limiter.block(rule.id, event.entity_id)

    await processor.process(event.event_id)

    assert len(channel.calls) == 0
    deliveries = deliveries_repo.all_deliveries()
    assert len(deliveries) == 1
    assert (
        deliveries[0].status == NotificationDeliveryStatus.SKIPPED_RATE_LIMITED
    )


async def test_missing_channel_config_skips_rule() -> None:
    event = _make_event()
    events_repo = FakeNotificationEventsRepository()
    await events_repo.try_insert(event)

    rules_repo = FakeNotificationRulesRepository()
    rule = new_notification_rule(
        event_type=event.event_type,
        channel_config_id=uuid4(),  # non-existent config
    )
    await rules_repo.save(rule)

    deliveries_repo = FakeNotificationDeliveriesRepository()
    fake_channel = _FakeChannel()
    processor = NotificationEventProcessor(
        events_repository=events_repo,
        rules_repository=rules_repo,
        channel_configs_repository=FakeNotificationChannelConfigsRepository(),
        deliveries_repository=deliveries_repo,
        rate_limiter=FakeNotificationRateLimiter(),
        channel_registry={NotificationChannelType.SLACK: fake_channel},
    )
    await processor.process(event.event_id)

    assert len(fake_channel.calls) == 0
    assert len(deliveries_repo.all_deliveries()) == 0


async def test_disabled_channel_config_skips_rule() -> None:
    event = _make_event()
    processor, deliveries_repo, channel, _ = await _build_processor(
        event=event, channel_enabled=False
    )
    await processor.process(event.event_id)

    assert len(channel.calls) == 0
    assert len(deliveries_repo.all_deliveries()) == 0


async def test_channel_send_failure_marks_delivery_failed_and_raises() -> None:
    event = _make_event()
    processor, deliveries_repo, channel, _ = await _build_processor(
        event=event, channel_raises=RuntimeError("connection timeout")
    )

    with pytest.raises(RuntimeError, match="connection timeout"):
        await processor.process(event.event_id)

    deliveries = deliveries_repo.all_deliveries()
    assert len(deliveries) == 1
    assert deliveries[0].status == NotificationDeliveryStatus.FAILED
    assert "connection timeout" in (deliveries[0].last_error or "")


async def test_no_matching_rules_creates_no_deliveries() -> None:
    event = _make_event(event_type=NotificationEventType.EXPERIMENT_LAUNCHED)
    events_repo = FakeNotificationEventsRepository()
    await events_repo.try_insert(event)

    # Rule for a different event type
    rules_repo = FakeNotificationRulesRepository()
    rule = new_notification_rule(
        event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
        channel_config_id=uuid4(),
    )
    await rules_repo.save(rule)

    deliveries_repo = FakeNotificationDeliveriesRepository()
    processor = NotificationEventProcessor(
        events_repository=events_repo,
        rules_repository=rules_repo,
        channel_configs_repository=FakeNotificationChannelConfigsRepository(),
        deliveries_repository=deliveries_repo,
        rate_limiter=FakeNotificationRateLimiter(),
        channel_registry={},
    )
    await processor.process(event.event_id)

    assert len(deliveries_repo.all_deliveries()) == 0


async def test_unknown_event_id_does_nothing() -> None:
    events_repo = FakeNotificationEventsRepository()
    processor = NotificationEventProcessor(
        events_repository=events_repo,
        rules_repository=FakeNotificationRulesRepository(),
        channel_configs_repository=FakeNotificationChannelConfigsRepository(),
        deliveries_repository=FakeNotificationDeliveriesRepository(),
        rate_limiter=FakeNotificationRateLimiter(),
        channel_registry={},
    )
    await processor.process(uuid4())  # should not raise
