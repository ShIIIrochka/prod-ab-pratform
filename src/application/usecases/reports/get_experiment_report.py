"""Use case: получить отчёт по эксперименту.

Соответствие ТЗ:
  5.2 — временное окно: from_time включительно, to_time исключительно
  5.3 — отчёт по всему эксперименту и по каждому варианту отдельно
  5.4 — метрики берутся только из конфига эксперимента (target + additional),
        возвращается контекст расчёта, динамика по дням только для дней с данными
Критерии:
  B6-1 — фильтр по периоду
  B6-2 — разрез по вариантам
  B6-3 — показываются метрики из конфигурации эксперимента
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

        # Нормализуем временные метки (ТЗ 5.2: from включительно, to исключительно)
        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=UTC)
        if to_time.tzinfo is None:
            to_time = to_time.replace(tzinfo=UTC)

        # Собираем уникальные ключи метрик из конфига эксперимента (ТЗ 5.4.1)
        # metric_keys: list[str] = []
        # if experiment.target_metric_key:
        #     metric_keys.append(experiment.target_metric_key)
        # for mk in experiment.metric_keys or []:
        #     if mk not in metric_keys:
        #         metric_keys.append(mk)
        if experiment.target_metric_key:
            metric_keys = list(
                set(experiment.metric_keys + [experiment.target_metric_key])
            )
        else:
            metric_keys = list(set(experiment.metric_keys))

        # Загружаем метрики из каталога одним проходом
        metrics_map: dict[str, Metric] = {}
        for mk in metric_keys:
            metric = await self._metrics_repository.get_by_key(mk)
            if metric:
                metrics_map[mk] = metric

        # Загружаем события эксперимента, сгруппированные по варианту
        events_by_variant = (
            await self._events_repository.get_by_experiment_grouped_by_variant(
                experiment_id=experiment_id,
                from_time=from_time,
                to_time=to_time,
                attribution_status=AttributionStatus.ATTRIBUTED,
            )
        )

        # Строим отчёт по каждому варианту эксперимента (ТЗ 5.3)
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
