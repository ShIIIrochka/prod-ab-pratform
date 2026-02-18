from __future__ import annotations

from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.metric import Metric


class CreateMetricUseCase:
    def __init__(
        self,
        metrics_repository: MetricsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._metrics_repository = metrics_repository
        self._uow = uow

    async def execute(
        self,
        key: str,
        name: str,
        calculation_rule: str,
        requires_exposure: bool = False,
        description: str | None = None,
    ) -> Metric:
        existing = await self._metrics_repository.get_by_key(key)
        if existing:
            msg = f"Metric with key '{key}' already exists"
            raise ValueError(msg)

        metric = Metric(
            key=key,
            name=name,
            calculation_rule=calculation_rule,
            requires_exposure=requires_exposure,
            description=description,
        )
        async with self._uow:
            await self._metrics_repository.save(metric)
        return metric
