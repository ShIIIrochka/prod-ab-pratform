from abc import ABC, abstractmethod

from src.domain.aggregates.event import Event


class PendingEventsStorePort(ABC):
    @abstractmethod
    async def put(
        self,
        event: Event,
        ttl_seconds: int | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, event_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_by_decision_id(self, decision_id: str) -> list[Event]:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_event_ids(self, event_ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_event_id(self, event_id: str) -> Event | None:
        raise NotImplementedError
