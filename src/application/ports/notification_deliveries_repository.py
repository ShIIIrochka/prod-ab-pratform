from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.notification_delivery import NotificationDelivery


class NotificationDeliveriesRepositoryPort(ABC):
    @abstractmethod
    async def save(self, delivery: NotificationDelivery) -> None: ...

    @abstractmethod
    async def get(
        self, event_id: UUID, rule_id: UUID
    ) -> NotificationDelivery | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_event(self, event_id: UUID) -> list[NotificationDelivery]:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[NotificationDelivery]:
        raise NotImplementedError
