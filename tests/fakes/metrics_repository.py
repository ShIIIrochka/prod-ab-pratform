"""Fake MetricsRepository — in-memory storage inheriting from port."""

from __future__ import annotations

from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.domain.aggregates.metric import Metric


class FakeMetricsRepository(MetricsRepositoryPort):
    """In-memory metrics for unit tests."""

    def __init__(self) -> None:
        self._by_key: dict[str, Metric] = {}

    async def get_by_key(self, key: str) -> Metric | None:
        return self._by_key.get(key)

    async def get_by_keys(self, keys: list[str]) -> dict[str, Metric]:
        return {k: m for k, m in self._by_key.items() if k in keys}

    async def save(self, metric: Metric) -> None:
        self._by_key[metric.key] = metric

    async def list_all(self) -> list[Metric]:
        return list(self._by_key.values())

    def add(self, metric: Metric) -> None:
        """Helper to populate for tests."""
        self._by_key[metric.key] = metric
