from __future__ import annotations

from uuid import UUID

from src.application.ports.notification_deliveries_repository import (
    NotificationDeliveriesRepositoryPort,
)
from src.domain.entities.notification_delivery import NotificationDelivery
from src.infra.adapters.db.models.notification_delivery import (
    NotificationDeliveryModel,
)


class NotificationDeliveriesRepository(NotificationDeliveriesRepositoryPort):
    async def save(self, delivery: NotificationDelivery) -> None:
        existing = await NotificationDeliveryModel.get_or_none(id=delivery.id)
        model = NotificationDeliveryModel.from_domain(delivery)
        if existing:
            await model.save(force_update=True)
        else:
            await model.save()

    async def get(
        self, event_id: UUID, rule_id: UUID
    ) -> NotificationDelivery | None:
        model = await NotificationDeliveryModel.get_or_none(
            event_id=event_id, rule_id=rule_id
        )
        return model.to_domain() if model else None

    async def list_by_event(self, event_id: UUID) -> list[NotificationDelivery]:
        models = (
            await NotificationDeliveryModel.filter(event_id=event_id)
            .order_by("-created_at")
            .all()
        )
        return [m.to_domain() for m in models]

    async def list_recent(self, limit: int = 100) -> list[NotificationDelivery]:
        models = (
            await NotificationDeliveryModel.all()
            .order_by("-created_at")
            .limit(limit)
        )
        return [m.to_domain() for m in models]
