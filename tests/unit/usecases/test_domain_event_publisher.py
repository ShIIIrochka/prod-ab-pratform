"""Unit tests for DomainEventPublisher mapping and dispatching logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.services.domain_event_publisher import DomainEventPublisher
from src.application.services.notification_dispatcher import (
    NotificationDispatcher,
)
from src.domain.events.experiment import (
    ExperimentEventType,
    ExperimentStatusChanged,
    GuardrailTriggered,
)
from tests.fakes.notification_events_repository import (
    FakeNotificationEventsRepository,
)
from tests.fakes.notification_task_enqueuer import FakeNotificationTaskEnqueuer


pytestmark = pytest.mark.asyncio


def _make_publisher() -> tuple[
    DomainEventPublisher, FakeNotificationTaskEnqueuer
]:
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=FakeNotificationEventsRepository(),
        task_enqueuer=enqueuer,
    )
    return DomainEventPublisher(dispatcher=dispatcher), enqueuer


async def test_experiment_status_changed_dispatched() -> None:
    publisher, enqueuer = _make_publisher()
    event = ExperimentStatusChanged(
        event_type=ExperimentEventType.LAUNCHED,
        experiment_id=uuid4(),
        experiment_name="My Exp",
        flag_key="flag_a",
        owner_id="owner-1",
        status="running",
        version=1,
    )
    await publisher.publish(event)

    assert len(enqueuer.enqueued) == 1


async def test_guardrail_triggered_dispatched() -> None:
    publisher, enqueuer = _make_publisher()
    event = GuardrailTriggered(
        experiment_id=uuid4(),
        experiment_name="My Exp",
        flag_key="flag_b",
        owner_id="owner-1",
        metric_key="error_rate",
        threshold=0.05,
        actual_value=0.12,
        action="pause",
        triggered_at=datetime.now(UTC),
        version=1,
    )
    await publisher.publish(event)

    assert len(enqueuer.enqueued) == 1


async def test_all_lifecycle_event_types_map_to_notification_events() -> None:
    """Every ExperimentEventType must produce a queued notification."""
    for event_type in ExperimentEventType:
        publisher, enqueuer = _make_publisher()
        event = ExperimentStatusChanged(
            event_type=event_type,
            experiment_id=uuid4(),
            experiment_name="Exp",
            flag_key="f",
            owner_id="o",
            status=event_type.value,
            version=1,
        )
        await publisher.publish(event)
        assert len(enqueuer.enqueued) == 1, f"No notification for {event_type}"


async def test_publish_from_aggregate_pops_events() -> None:
    """publish_from drains the aggregate's domain event queue."""
    from src.domain.aggregates.experiment import Experiment
    from src.domain.entities.variant import Variant
    from src.domain.value_objects.experiment_status import ExperimentStatus

    exp = Experiment(
        flag_key="x",
        name="Test",
        status=ExperimentStatus.DRAFT,
        version=1,
        audience_fraction=0.5,
        variants=[
            Variant(
                id=uuid4(),
                name="control",
                value="A",
                weight=0.25,
                is_control=True,
            ),
            Variant(
                id=uuid4(),
                name="treatment",
                value="B",
                weight=0.25,
                is_control=False,
            ),
        ],
        targeting_rule=None,
        owner_id="owner-1",
    )

    exp.send_to_review()
    assert len(exp._domain_events) == 1

    publisher, enqueuer = _make_publisher()
    await publisher.publish_from(exp)

    # Events consumed from aggregate
    assert len(exp._domain_events) == 0
    assert len(enqueuer.enqueued) == 1


async def test_publish_from_aggregate_idempotent_on_second_call() -> None:
    """Calling publish_from twice only enqueues once (events already popped)."""
    from src.domain.aggregates.experiment import Experiment
    from src.domain.entities.variant import Variant
    from src.domain.value_objects.experiment_status import ExperimentStatus

    exp = Experiment(
        flag_key="x",
        name="Test",
        status=ExperimentStatus.DRAFT,
        version=1,
        audience_fraction=0.5,
        variants=[
            Variant(
                id=uuid4(),
                name="control",
                value="A",
                weight=0.25,
                is_control=True,
            ),
            Variant(
                id=uuid4(),
                name="treatment",
                value="B",
                weight=0.25,
                is_control=False,
            ),
        ],
        targeting_rule=None,
        owner_id="owner-1",
    )
    exp.send_to_review()

    publisher, enqueuer = _make_publisher()
    await publisher.publish_from(exp)
    await publisher.publish_from(exp)  # second call: no events left

    assert len(enqueuer.enqueued) == 1


async def test_dedup_same_domain_event_twice() -> None:
    """Publishing the same event payload twice only enqueues once."""
    publisher, enqueuer = _make_publisher()
    entity_id = uuid4()
    event = ExperimentStatusChanged(
        event_type=ExperimentEventType.PAUSED,
        experiment_id=entity_id,
        experiment_name="Exp",
        flag_key="f",
        owner_id="o",
        status="paused",
        version=2,
    )
    await publisher.publish(event)
    await publisher.publish(event)  # same version → same event_id → deduped

    assert len(enqueuer.enqueued) == 1
