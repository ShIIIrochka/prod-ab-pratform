from __future__ import annotations

from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.domain.aggregates.metric import Metric


class GetMetricUseCase:
    def __init__(self, metrics_repository: MetricsRepositoryPort) -> None:
        self._metrics_repository = metrics_repository

    async def execute(self, key: str) -> Metric:
        metric = await self._metrics_repository.get_by_key(key)
        if not metric:
            msg = f"Metric '{key}' not found"
            raise ValueError(msg)
        return metric
