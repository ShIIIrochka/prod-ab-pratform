from __future__ import annotations

from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.domain.aggregates.metric import Metric
from src.infra.adapters.db.models.metric import MetricModel


class MetricsRepository(MetricsRepositoryPort):
    async def get_by_key(self, key: str) -> Metric | None:
        model = await MetricModel.get_or_none(key=key)
        if model is None:
            return None
        return model.to_domain()

    async def save(self, metric: Metric) -> None:
        existing = await MetricModel.get_or_none(key=metric.key)
        model = MetricModel.from_domain(metric)
        if existing:
            await model.save(force_update=True)
        else:
            await model.save()

    async def list_all(self) -> list[Metric]:
        models = await MetricModel.all()
        return [m.to_domain() for m in models]
