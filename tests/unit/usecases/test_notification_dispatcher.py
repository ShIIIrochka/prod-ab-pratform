"""Unit tests for NotificationDispatcher: dedup and enqueue behavior."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.services.notification_dispatcher import (
    NotificationDispatcher,
)
from src.domain.value_objects.notification_event import (
    NotificationEvent,
    make_notification_event_id,
)
from src.domain.value_objects.notification_event_type import (
    NotificationEventType,
)
from tests.fakes.notification_events_repository import (
    FakeNotificationEventsRepository,
)
from tests.fakes.notification_task_enqueuer import FakeNotificationTaskEnqueuer


pytestmark = pytest.mark.asyncio


def _make_event(
    event_type: str = NotificationEventType.EXPERIMENT_LAUNCHED,
    version: int = 1,
) -> NotificationEvent:
    entity_id = uuid4()
    return NotificationEvent(
        event_id=make_notification_event_id(event_type, entity_id, version),
        event_type=event_type,
        entity_type="experiment",
        entity_id=entity_id,
        payload={"experiment_name": "Test", "status": "running"},
    )


async def test_dispatch_new_event_enqueues_task() -> None:
    repo = FakeNotificationEventsRepository()
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=repo, task_enqueuer=enqueuer
    )

    event = _make_event()
    await dispatcher.dispatch(event)

    assert len(enqueuer.enqueued) == 1
    assert enqueuer.enqueued[0] == event.event_id


async def test_dispatch_duplicate_event_does_not_enqueue() -> None:
    repo = FakeNotificationEventsRepository()
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=repo, task_enqueuer=enqueuer
    )

    event = _make_event()
    await dispatcher.dispatch(event)
    await dispatcher.dispatch(event)  # second time: duplicate

    assert len(enqueuer.enqueued) == 1


async def test_dispatch_different_events_enqueue_separately() -> None:
    repo = FakeNotificationEventsRepository()
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=repo, task_enqueuer=enqueuer
    )

    e1 = _make_event(NotificationEventType.EXPERIMENT_LAUNCHED, version=1)
    e2 = _make_event(NotificationEventType.EXPERIMENT_PAUSED, version=2)
    await dispatcher.dispatch(e1)
    await dispatcher.dispatch(e2)

    assert len(enqueuer.enqueued) == 2


async def test_dispatch_repo_failure_does_not_raise() -> None:
    """If repo.try_insert raises, dispatcher should swallow the error."""

    class BrokenRepo(FakeNotificationEventsRepository):
        async def try_insert(self, event: NotificationEvent) -> bool:
            raise RuntimeError("DB is down")

    repo = BrokenRepo()
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=repo, task_enqueuer=enqueuer
    )

    event = _make_event()
    await dispatcher.dispatch(event)  # should not raise

    assert len(enqueuer.enqueued) == 0


async def test_deterministic_event_id_is_stable() -> None:
    """make_notification_event_id with same inputs always returns same UUID."""
    entity_id = uuid4()
    event_type = NotificationEventType.GUARDRAIL_TRIGGERED
    id1 = make_notification_event_id(event_type, entity_id, 3)
    id2 = make_notification_event_id(event_type, entity_id, 3)
    id3 = make_notification_event_id(
        event_type, entity_id, 4
    )  # different version

    assert id1 == id2
    assert id1 != id3
