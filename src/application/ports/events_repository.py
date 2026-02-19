from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.aggregates.event import AttributionStatus, Event


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
        """Получить только exposure-события по decision_id."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_experiment(
        self,
        experiment_id: UUID,
        from_time: datetime,
        to_time: datetime,
        attribution_status: AttributionStatus | None = None,
    ) -> list[Event]:
        """Получить все события по эксперименту в заданном временном окне.

        Выполняет JOIN events → decisions → experiment_id.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_experiment_and_variant(
        self,
        experiment_id: UUID,
        variant_name: str,
        from_time: datetime,
        to_time: datetime,
        attribution_status: AttributionStatus | None = None,
    ) -> list[Event]:
        """Получить события по эксперименту и варианту в заданном временном окне."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_experiment_grouped_by_variant(
        self,
        experiment_id: UUID,
        from_time: datetime,
        to_time: datetime,
        attribution_status: AttributionStatus | None = None,
    ) -> dict[str, list[Event]]:
        """Получить все события эксперимента, сгруппированные по имени варианта.

        Выполняет 2 запроса вместо N (по числу вариантов):
        1. Загружает decisions эксперимента → маппинг decision_id → variant_name
        2. Загружает все события по decision_ids за указанный период
        """
        raise NotImplementedError
