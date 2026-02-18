from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.aggregates.event_type import EventType


class EventTypesRepositoryPort(ABC):
    @abstractmethod
    async def save(self, event_type: EventType) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_key(self, key: str) -> EventType | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[EventType]:
        raise NotImplementedError
