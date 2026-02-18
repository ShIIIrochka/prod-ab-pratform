from __future__ import annotations

from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.domain.aggregates.metric import Metric


class ListMetricsUseCase:
    def __init__(self, metrics_repository: MetricsRepositoryPort) -> None:
        self._metrics_repository = metrics_repository

    async def execute(self) -> list[Metric]:
        return await self._metrics_repository.list_all()
