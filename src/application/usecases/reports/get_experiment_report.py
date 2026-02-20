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
from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.metric import Metric
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
        experiment: (
            Experiment | None
        ) = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=UTC)
        if to_time.tzinfo is None:
            to_time = to_time.replace(tzinfo=UTC)

        if experiment.target_metric_key:
            metric_keys = list(
                set(experiment.metric_keys + [experiment.target_metric_key])
            )
        else:
            metric_keys = list(set(experiment.metric_keys))

        metrics_map: dict[
            str, Metric
        ] = await self._metrics_repository.get_by_keys(metric_keys)

        # Загружаем события эксперимента, сгруппированные по варианту
        events_by_variant = (
            await self._events_repository.get_by_experiment_grouped_by_variant(
                experiment_id=experiment_id,
                from_time=from_time,
                to_time=to_time,
                attribution_status=AttributionStatus.ATTRIBUTED,
            )
        )

        # Строим отчёт по каждому варианту эксперимента
        variant_reports: list[VariantReportResponse] = []
        for variant in experiment.variants:
            events = events_by_variant.get(variant.name, [])

            metric_values: list[MetricValueResponse] = []
            dynamics_list: list[MetricDynamics] = []

            for mk in metric_keys:
                metric = metrics_map.get(mk)
                if metric is None:
                    continue

                value = calculate_metric(metric, events)
                metric_values.append(
                    MetricValueResponse(
                        metric_key=metric.key,
                        metric_name=metric.name,
                        value=value,
                        is_primary=(mk == experiment.target_metric_key),
                        aggregation_unit=metric.aggregation_unit.value,
                    )
                )

                # Динамика — только дни, в которых есть хотя бы одно событие
                day_points = _compute_daily_dynamics(
                    metric, events, from_time, to_time
                )
                if day_points:
                    dynamics_list.append(
                        MetricDynamics(metric_key=metric.key, points=day_points)
                    )

            variant_reports.append(
                VariantReportResponse(
                    variant_name=variant.name,
                    is_control=variant.is_control,
                    metrics=metric_values,
                    dynamics=dynamics_list,
                )
            )

        units = {
            mk: metrics_map[mk].aggregation_unit.value for mk in metrics_map
        }
        unique_units = set(units.values())
        top_level_unit: str | None = (
            next(iter(unique_units)) if len(unique_units) == 1 else None
        )

        return ExperimentReportResponse(
            experiment_id=experiment_id,
            experiment_name=experiment.name,
            from_time=from_time,
            to_time=to_time,
            variants=variant_reports,
            aggregation_unit=top_level_unit,
            context={
                "attribution": "attributed_only",
                "window_from": from_time.isoformat(),
                "window_to": to_time.isoformat(),
                "metric_keys": metric_keys,
            },
        )


def _compute_daily_dynamics(
    metric: Metric,
    events: list[Event],
    from_time: datetime,
    to_time: datetime,
) -> list[MetricDynamicsPoint]:
    """Группирует события по дням и вычисляет метрику — только для дней с данными."""
    buckets: dict[datetime, list[Event]] = defaultdict(list)
    for event in events:
        ts = event.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        day_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets[day_start].append(event)

    if not buckets:
        return []

    points: list[MetricDynamicsPoint] = []
    current = from_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    end = to_time if to_time.tzinfo else to_time.replace(tzinfo=UTC)

    while current < end:
        day_events = buckets.get(current)
        if day_events:
            value = calculate_metric(metric, day_events)
            points.append(MetricDynamicsPoint(timestamp=current, value=value))
        current += timedelta(days=1)

    return points
