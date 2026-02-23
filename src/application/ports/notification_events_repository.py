from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.value_objects.notification_event import NotificationEvent


class NotificationEventsRepositoryPort(ABC):
    @abstractmethod
    async def try_insert(self, event: NotificationEvent) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, event_id: UUID) -> NotificationEvent | None:
        raise NotImplementedError
