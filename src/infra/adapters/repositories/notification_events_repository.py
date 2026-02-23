from __future__ import annotations

from uuid import UUID

from tortoise.exceptions import IntegrityError

from src.application.ports.notification_events_repository import (
    NotificationEventsRepositoryPort,
)
from src.domain.value_objects.notification_event import NotificationEvent
from src.infra.adapters.db.models.notification_event import (
    NotificationEventModel,
)


class NotificationEventsRepository(NotificationEventsRepositoryPort):
    async def try_insert(self, event: NotificationEvent) -> bool:
        model = NotificationEventModel.from_domain(event)
        try:
            await model.save()
            return True
        except IntegrityError:
            return False

    async def get_by_id(self, event_id: UUID) -> NotificationEvent | None:
        model = await NotificationEventModel.get_or_none(id=event_id)
        return model.to_domain() if model else None
