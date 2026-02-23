from abc import ABC, abstractmethod
from uuid import UUID


class NotificationTaskEnqueuerPort(ABC):
    @abstractmethod
    def enqueue(self, event_id: UUID) -> None:
        raise NotImplementedError
