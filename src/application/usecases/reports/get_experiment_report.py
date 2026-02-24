from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.application.dto.reports import (
    DataQualitySummary,
    ExperimentReportResponse,
    MetricDynamics,
    MetricDynamicsPoint,
    MetricValueResponse,
    OverallReportResponse,
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


def _to_unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


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

        # Load experiment events grouped by variant (single batched query)
        events_by_variant = (
            await self._events_repository.get_by_experiment_grouped_by_variant(
                experiment_id=experiment_id,
                from_time=from_time,
                to_time=to_time,
                attribution_status=AttributionStatus.ATTRIBUTED,
            )
        )

        # Build per-variant reports
        variant_reports: list[VariantReportResponse] = []
        for variant in experiment.variants:
            events = events_by_variant.get(variant.name, [])
            metric_values, dynamics_list = _build_metric_results(
                metric_keys,
                metrics_map,
                events,
                from_time,
                to_time,
                primary_metric_key=experiment.target_metric_key,
            )
            variant_reports.append(
                VariantReportResponse(
                    variant_name=variant.name,
                    is_control=variant.is_control,
                    metrics=metric_values,
                    dynamics=dynamics_list,
                )
            )

        # Build overall report — recalculate on the combined event set (not
        # an average of variant values, which would be wrong for RATIO/percentile)
        all_events: list[Event] = []
        for events in events_by_variant.values():
            all_events.extend(events)

        overall_metrics, overall_dynamics = _build_metric_results(
            metric_keys,
            metrics_map,
            all_events,
            from_time,
            to_time,
            primary_metric_key=experiment.target_metric_key,
        )
        overall = OverallReportResponse(
            metrics=overall_metrics,
            dynamics=overall_dynamics,
        )

        variant_event_counts = {
            v: len(evs) for v, evs in events_by_variant.items()
        }
        total_attributed_events = sum(
            len(evs) for evs in events_by_variant.values()
        )
        data_quality = DataQualitySummary(
            variant_event_counts=variant_event_counts,
            total_attributed_events=total_attributed_events,
        )

        return ExperimentReportResponse(
            experiment_id=experiment_id,
            experiment_name=experiment.name,
            from_time=_to_unix(from_time),
            to_time=_to_unix(to_time),
            overall=overall,
            variants=variant_reports,
            data_quality=data_quality,
            context={
                "attribution": "attributed_only",
                "window_from": from_time.isoformat(),
                "window_to": to_time.isoformat(),
                "metric_keys": metric_keys,
            },
        )


def _build_metric_results(
    metric_keys: list[str],
    metrics_map: dict[str, Metric],
    events: list[Event],
    from_time: datetime,
    to_time: datetime,
    primary_metric_key: str | None,
) -> tuple[list[MetricValueResponse], list[MetricDynamics]]:
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
                is_primary=(mk == primary_metric_key),
                aggregation_unit=metric.aggregation_unit.value,
            )
        )

        day_points = _compute_daily_dynamics(metric, events, from_time, to_time)
        if day_points:
            dynamics_list.append(
                MetricDynamics(metric_key=metric.key, points=day_points)
            )

    return metric_values, dynamics_list


def _compute_daily_dynamics(
    metric: Metric,
    events: list[Event],
    from_time: datetime,
    to_time: datetime,
) -> list[MetricDynamicsPoint]:
    """Group events by day and compute metric — only for days with data."""
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
            points.append(
                MetricDynamicsPoint(timestamp=_to_unix(current), value=value)
            )
        current += timedelta(days=1)

    return points
