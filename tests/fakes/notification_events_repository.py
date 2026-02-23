from uuid import UUID

from src.application.ports.notification_events_repository import (
    NotificationEventsRepositoryPort,
)
from src.domain.value_objects.notification_event import NotificationEvent


class FakeNotificationEventsRepository(NotificationEventsRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[UUID, NotificationEvent] = {}

    async def try_insert(self, event: NotificationEvent) -> bool:
        if event.event_id in self._store:
            return False
        self._store[event.event_id] = event
        return True

    async def get_by_id(self, event_id: UUID) -> NotificationEvent | None:
        return self._store.get(event_id)
