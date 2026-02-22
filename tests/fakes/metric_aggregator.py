"""Fake MetricAggregator — configurable return values for unit tests."""

from __future__ import annotations

from uuid import UUID

from src.application.ports.metric_aggregator import MetricAggregatorPort
from src.domain.aggregates.event import Event
from src.domain.aggregates.metric import Metric


class FakeMetricAggregator(MetricAggregatorPort):
    """In-memory metric aggregator for unit tests.

    Configurable via set_value(experiment_id, metric_key, value) so tests
    can simulate different guardrail thresholds.
    """

    def __init__(self) -> None:
        # (experiment_id, metric_key) -> value
        self._values: dict[tuple[UUID, str], float] = {}
        self._default_value: float = 0.0

    def set_value(
        self, experiment_id: UUID, metric_key: str, value: float
    ) -> None:
        """Set the value that get_value will return for this experiment/metric."""
        self._values[(experiment_id, metric_key)] = value

    def set_default_value(self, value: float) -> None:
        """Default when no explicit value is set."""
        self._default_value = value

    async def update(
        self,
        experiment_id: UUID,
        event: Event,
        metrics: list[Metric],
        max_ttl_seconds: int,
    ) -> None:
        """No-op for unit tests — we only care about get_value behavior."""
        pass

    async def get_value(
        self,
        experiment_id: UUID,
        metric: Metric,
        window_minutes: int,
    ) -> float:
        key = (experiment_id, metric.key)
        return self._values.get(key, self._default_value)
