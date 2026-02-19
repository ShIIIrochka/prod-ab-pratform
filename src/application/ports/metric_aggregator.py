from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.aggregates.event import Event
from src.domain.aggregates.metric import Metric


class MetricAggregatorPort(ABC):
    """Порт для инкрементальной агрегации метрик через Redis.

    Вместо загрузки всех событий за окно при каждой проверке guardrail-а,
    агрегаты обновляются в реальном времени при сохранении каждого события.
    Guardrail checker читает уже готовые агрегаты (O(k) по кол-ву buckets).
    """

    @abstractmethod
    async def update(
        self,
        experiment_id: UUID,
        event: Event,
        metrics: list[Metric],
        max_ttl_seconds: int,
    ) -> None:
        """Обновить агрегаты в Redis при приходе нового ATTRIBUTED-события.

        Args:
            experiment_id: UUID эксперимента.
            event: Обработанное событие со статусом ATTRIBUTED.
            metrics: Список метрик guardrails этого эксперимента.
            max_ttl_seconds: TTL каждого bucket-ключа в секундах.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_value(
        self,
        experiment_id: UUID,
        metric: Metric,
        window_minutes: int,
    ) -> float:
        """Вычислить значение метрики за последние window_minutes минут.

        Читает агрегированные bucket-ключи из Redis без обращения к PostgreSQL.
        """
        raise NotImplementedError
