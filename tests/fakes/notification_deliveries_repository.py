from uuid import UUID

from src.application.ports.notification_deliveries_repository import (
    NotificationDeliveriesRepositoryPort,
)
from src.domain.entities.notification_delivery import NotificationDelivery


class FakeNotificationDeliveriesRepository(
    NotificationDeliveriesRepositoryPort
):
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], NotificationDelivery] = {}

    async def save(self, delivery: NotificationDelivery) -> None:
        self._store[(delivery.event_id, delivery.rule_id)] = delivery

    async def get(
        self, event_id: UUID, rule_id: UUID
    ) -> NotificationDelivery | None:
        return self._store.get((event_id, rule_id))

    async def list_by_event(self, event_id: UUID) -> list[NotificationDelivery]:
        return [d for d in self._store.values() if d.event_id == event_id]

    async def list_recent(self, limit: int = 100) -> list[NotificationDelivery]:
        items = sorted(
            self._store.values(), key=lambda d: d.created_at, reverse=True
        )
        return items[:limit]

    def all_deliveries(self) -> list[NotificationDelivery]:
        return list(self._store.values())
