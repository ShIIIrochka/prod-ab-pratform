from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.aggregates.event import Event


class EventsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, event: Event) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, event_id: UUID) -> Event | None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, event_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_by_decision_id(
        self, decision_id: str, event_type_key: str | None = None
    ) -> list[Event]:
        raise NotImplementedError

    @abstractmethod
    async def get_exposure_by_decision_id(
        self, decision_id: str
    ) -> list[Event]:
        """Получить только exposure-события по decision_id.

        Используется в отчётах и при расчёте атрибуции.

        Args:
            decision_id: ID решения

        Returns:
            Список exposure-событий
        """
        raise NotImplementedError
