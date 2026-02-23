from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.aggregates.metric import AggregationUnit, Metric
from src.domain.services.metric_calculator import calculate_metric


def _event(subject_id: str, event_type: str, **props) -> Event:
    return Event(
        id=uuid4(),
        event_type_key=event_type,
        decision_id=uuid4(),
        subject_id=subject_id,
        timestamp=datetime.now(UTC),
        props=props,
        attribution_status=AttributionStatus.ATTRIBUTED,
    )


def test_percentile_p95_basic() -> None:
    metric = Metric(
        key="p95_latency",
        name="P95 Latency",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"request","property":"ms","percentile":95}',
        aggregation_unit=AggregationUnit.EVENT,
    )
    events = [_event(f"u{i}", "request", ms=float(i)) for i in range(1, 21)]
    result = calculate_metric(metric, events)
    assert result >= 18.0


def test_percentile_dsl_p95() -> None:
    metric = Metric(
        key="p95_dur",
        name="P95 Duration",
        calculation_rule="P95(latency, duration_ms)",
        aggregation_unit=AggregationUnit.EVENT,
    )
    events = [
        _event(f"u{i}", "latency", duration_ms=float(i * 10))
        for i in range(1, 11)
    ]
    result = calculate_metric(metric, events)
    assert result > 0.0


def test_percentile_p50_is_median() -> None:
    metric = Metric(
        key="p50",
        name="Median",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"req","property":"ms","percentile":50}',
        aggregation_unit=AggregationUnit.EVENT,
    )
    # Values: 10, 20, 30, 40, 50 — median ~30
    events = [
        _event("u1", "req", ms=10.0),
        _event("u2", "req", ms=20.0),
        _event("u3", "req", ms=30.0),
        _event("u4", "req", ms=40.0),
        _event("u5", "req", ms=50.0),
    ]
    result = calculate_metric(metric, events)
    assert 20.0 <= result <= 40.0


def test_percentile_empty_events_returns_zero() -> None:
    metric = Metric(
        key="p99_empty",
        name="P99 Empty",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"req","property":"ms","percentile":99}',
    )
    assert calculate_metric(metric, []) == 0.0


def test_percentile_no_matching_event_type_returns_zero() -> None:
    metric = Metric(
        key="p99_no_match",
        name="P99 No Match",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"request","property":"ms","percentile":99}',
    )
    events = [_event("u1", "click", ms=100.0)]
    assert calculate_metric(metric, events) == 0.0


def test_percentile_non_numeric_props_skipped() -> None:
    metric = Metric(
        key="p95_str",
        name="P95 String Props",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"req","property":"ms","percentile":95}',
    )
    events = [
        _event("u1", "req", ms="not_a_number"),
        _event("u2", "req", ms=100.0),
        _event("u3", "req", ms=200.0),
    ]
    result = calculate_metric(metric, events)
    # Only 2 numeric values processed
    assert result > 0.0


def test_percentile_single_value() -> None:
    metric = Metric(
        key="p95_single",
        name="P95 Single",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"req","property":"ms","percentile":95}',
    )
    events = [_event("u1", "req", ms=42.0)]
    result = calculate_metric(metric, events)
    assert result == 42.0


def test_percentile_user_level_aggregates_per_user() -> None:
    metric = Metric(
        key="p95_user",
        name="P95 User",
        calculation_rule='{"type":"PERCENTILE","event_type_key":"req","property":"ms","percentile":95}',
        aggregation_unit=AggregationUnit.USER,
    )
    # u1 2 events: 10 and 20 -> avg = 15
    # u2 1 event: 100
    events = [
        _event("u1", "req", ms=10.0),
        _event("u1", "req", ms=20.0),
        _event("u2", "req", ms=100.0),
    ]
    result = calculate_metric(metric, events)
    assert result > 0.0  # [15, 100] → P95 ~ 100


def test_sum_missing_property_returns_zero() -> None:
    metric = Metric(
        key="sum_test",
        name="Sum Test",
        calculation_rule='{"type":"SUM","event_type_key":"purchase","property":"amount"}',
    )
    events = [_event("u1", "purchase")]  # no 'amount' prop
    assert calculate_metric(metric, events) == 0.0


def test_sum_numeric_property() -> None:
    metric = Metric(
        key="total_revenue",
        name="Total Revenue",
        calculation_rule='{"type":"SUM","event_type_key":"purchase","property":"amount"}',
    )
    events = [
        _event("u1", "purchase", amount=10.0),
        _event("u2", "purchase", amount=25.5),
        _event("u3", "purchase", amount=5.0),
    ]
    result = calculate_metric(metric, events)
    assert abs(result - 40.5) < 1e-6


def test_avg_empty_events_returns_zero() -> None:
    metric = Metric(
        key="avg_test",
        name="Avg Test",
        calculation_rule='{"type":"AVG","event_type_key":"session","property":"dur"}',
    )
    assert calculate_metric(metric, []) == 0.0


def test_avg_numeric() -> None:
    metric = Metric(
        key="avg_dur",
        name="Avg Duration",
        calculation_rule='{"type":"AVG","event_type_key":"session","property":"dur"}',
    )
    events = [
        _event("u1", "session", dur=10.0),
        _event("u2", "session", dur=20.0),
    ]
    result = calculate_metric(metric, events)
    assert abs(result - 15.0) < 1e-6
