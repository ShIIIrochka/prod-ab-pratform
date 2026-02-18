from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.aggregates.metric import Metric


class MetricsRepositoryPort(ABC):
    @abstractmethod
    async def get_by_key(self, key: str) -> Metric | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, metric: Metric) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[Metric]:
        raise NotImplementedError
