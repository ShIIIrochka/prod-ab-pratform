"""Use Case генерации отчёта по эксперименту.

Отчёт строится по атрибутированным событиям в заданном временном окне.
Для каждого варианта вычисляются значения выбранных метрик и суточная динамика.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.application.dto.reports import (
    ExperimentReportResponse,
    MetricDynamics,
    MetricDynamicsPoint,
    MetricValueResponse,
    VariantReportResponse,
)
from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.exceptions.decision import ExperimentNotFoundError
from src.domain.services.metric_calculator import calculate_metric


class GetExperimentReportUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        events_repository: EventsRepositoryPort,
        metrics_repository: MetricsRepositoryPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._events_repository = events_repository
        self._metrics_repository = metrics_repository

    async def execute(
        self,
        experiment_id: UUID,
        from_time: datetime,
        to_time: datetime,
    ) -> ExperimentReportResponse:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        # Собираем все ключи метрик: сначала target, потом остальные
        all_metric_keys: list[str] = []
        if experiment.target_metric_key:
            all_metric_keys.append(experiment.target_metric_key)
        for key in experiment.metric_keys:
            if key not in all_metric_keys:
                all_metric_keys.append(key)

        # Загружаем метрики из каталога
        metrics_map = {}
        for key in all_metric_keys:
            metric = await self._metrics_repository.get_by_key(key)
            if metric:
                metrics_map[key] = metric

        # Строим отчёт по каждому варианту
        variant_reports = []
        for variant in experiment.variants:
            events = (
                await self._events_repository.get_by_experiment_and_variant(
                    experiment_id=experiment_id,
                    variant_name=variant.name,
                    from_time=from_time,
                    to_time=to_time,
                    attribution_status=AttributionStatus.ATTRIBUTED,
                )
            )

            metric_values = []
            dynamics_list = []

            for metric_key, metric in metrics_map.items():
                value = calculate_metric(metric, events)
                metric_values.append(
                    MetricValueResponse(
                        metric_key=metric_key,
                        metric_name=metric.name,
                        value=value,
                        is_primary=(metric_key == experiment.target_metric_key),
                    )
                )

                # Суточная динамика
                day_points = _compute_daily_dynamics(
                    metric, events, from_time, to_time
                )
                dynamics_list.append(
                    MetricDynamics(metric_key=metric_key, points=day_points)
                )

            variant_reports.append(
                VariantReportResponse(
                    variant_name=variant.name,
                    metrics=metric_values,
                    dynamics=dynamics_list,
                )
            )

        return ExperimentReportResponse(
            experiment_id=experiment_id,
            experiment_name=experiment.name,
            from_time=from_time,
            to_time=to_time,
            variants=variant_reports,
            context={
                "attribution": "attributed_only",
                "aggregation_unit": "event",
                "window_from": from_time.isoformat(),
                "window_to": to_time.isoformat(),
            },
        )


def _compute_daily_dynamics(
    metric,
    events: list[Event],
    from_time: datetime,
    to_time: datetime,
) -> list[MetricDynamicsPoint]:
    """Группирует события по дням и вычисляет метрику для каждого дня."""
    # Группируем события по дате (UTC)
    buckets: dict[datetime, list[Event]] = defaultdict(list)
    for event in events:
        ts = event.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        day_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets[day_start].append(event)

    # Перебираем дни в окне
    points = []
    current = from_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    end = to_time
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    while current < end:
        day_events = buckets.get(current, [])
        value = calculate_metric(metric, day_events) if day_events else 0.0
        points.append(MetricDynamicsPoint(timestamp=current, value=value))
        current += timedelta(days=1)

    return points
