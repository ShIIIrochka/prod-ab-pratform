from uuid import UUID

from src.application.ports.notification_deliveries_repository import (
    NotificationDeliveriesRepositoryPort,
)
from src.domain.entities.notification_delivery import NotificationDelivery


class ListNotificationDeliveriesUseCase:
    def __init__(
        self, repository: NotificationDeliveriesRepositoryPort
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        event_id: UUID | None = None,
        limit: int = 100,
    ) -> list[NotificationDelivery]:
        if event_id is not None:
            return await self._repository.list_by_event(event_id)
        return await self._repository.list_recent(limit=limit)
