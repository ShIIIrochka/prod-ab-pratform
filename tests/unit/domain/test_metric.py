from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.aggregates.metric import AggregationUnit, Metric
from src.domain.services.metric_calculator import calculate_metric


def _make_event(subject_id: str, event_type_key: str, props=None) -> Event:
    return Event(
        id=uuid4(),
        event_type_key=event_type_key,
        decision_id=uuid4(),
        subject_id=subject_id,
        timestamp=datetime.now(UTC),
        props=props or {},
        attribution_status=AttributionStatus.ATTRIBUTED,
    )


def test_metric_has_key():
    """Metric должен использовать key как primary identifier."""
    metric = Metric(
        key="error_rate",
        name="Error Rate",
        calculation_rule='{"type":"RATIO"}',
    )
    assert metric.key == "error_rate"


def test_metric_key_is_unique_identifier():
    """Два разных Metric имеют разные key."""
    m1 = Metric(
        key="m1",
        name="M1",
        calculation_rule="COUNT(click)",
    )
    m2 = Metric(
        key="m2",
        name="M2",
        calculation_rule="COUNT(click)",
    )
    assert m1.key != m2.key


def test_metric_calculation_rule_stored():
    """calculation_rule сохраняется как есть."""
    rule = '{"type":"COUNT","event_type_key":"click"}'
    metric = Metric(key="ctr", name="CTR", calculation_rule=rule)
    assert metric.calculation_rule == rule


def test_metric_dsl_rule_stored():
    """DSL calculation_rule сохраняется без изменений."""
    metric = Metric(
        key="err", name="Err", calculation_rule="COUNT(error) / COUNT(exposure)"
    )
    assert metric.calculation_rule == "COUNT(error) / COUNT(exposure)"


def test_metric_aggregation_unit_default_event():
    """По умолчанию aggregation_unit = event."""
    metric = Metric(key="m", name="M", calculation_rule="{}")
    assert metric.aggregation_unit == AggregationUnit.EVENT


def test_metric_aggregation_unit_user():
    """Можно задать aggregation_unit = user."""
    metric = Metric(
        key="unique_conversions",
        name="Unique Conversions",
        calculation_rule='{"type":"COUNT","event_type_key":"conversion"}',
        aggregation_unit=AggregationUnit.USER,
    )
    assert metric.aggregation_unit == AggregationUnit.USER


def test_calculate_metric_event_count_multiple_events_same_user():
    """unit=event: COUNT считает все события, включая дубли по пользователю."""
    metric = Metric(
        key="clicks",
        name="Clicks",
        calculation_rule="COUNT(click)",
        aggregation_unit=AggregationUnit.EVENT,
    )
    events = [
        _make_event("u1", "click"),
        _make_event("u1", "click"),
        _make_event("u2", "click"),
    ]
    assert calculate_metric(metric, events) == 3.0


def test_calculate_metric_user_count_deduplicates():
    """unit=user: COUNT считает уникальных пользователей."""
    metric = Metric(
        key="unique_clicks",
        name="Unique Clicks",
        calculation_rule="COUNT(click)",
        aggregation_unit=AggregationUnit.USER,
    )
    events = [
        _make_event("u1", "click"),
        _make_event("u1", "click"),
        _make_event("u2", "click"),
    ]
    assert calculate_metric(metric, events) == 2.0


def test_calculate_metric_user_count_no_events():
    """unit=user: пустой список → 0."""
    metric = Metric(
        key="u",
        name="U",
        calculation_rule='{"type":"COUNT","event_type_key":"click"}',
        aggregation_unit=AggregationUnit.USER,
    )
    assert calculate_metric(metric, []) == 0.0


def test_calculate_metric_user_ratio():
    """unit=user: RATIO = уникальных конверсий / уникальных показов."""
    metric = Metric(
        key="cvr",
        name="CVR",
        calculation_rule="COUNT(conversion) / COUNT(exposure)",
        aggregation_unit=AggregationUnit.USER,
    )
    events = [
        _make_event("u1", "exposure"),
        _make_event("u1", "exposure"),
        _make_event("u2", "exposure"),
        _make_event("u1", "conversion"),
    ]
    # numerator=1, denominator=2
    result = calculate_metric(metric, events)
    assert abs(result - 0.5) < 1e-6


# Мне кажется доменный сервс не должен знать про то события с каким статусом нам присылают
# def test_calculate_metric_only_attributed_events_used():
#     """Только ATTRIBUTED-события включаются в расчёт."""
#     from src.domain.aggregates.event import AttributionStatus

#     metric = Metric(
#         key="clicks",
#         name="Clicks",
#         calculation_rule='{"type":"COUNT","event_type_key":"click"}',
#     )
#     pending_event = Event(
#         id=uuid4(),
#         event_type_key="click",
#         decision_id=uuid4(),
#         subject_id="u1",
#         timestamp=datetime.now(UTC),
#         props={},
#         attribution_status=AttributionStatus.PENDING,
#     )
#     attributed_event = _make_event("u2", "click")
#     assert calculate_metric(metric, [pending_event, attributed_event]) == 1.0


def test_calculate_metric_invalid_rule_returns_zero():
    """Невалидное правило → 0."""
    metric = Metric(key="bad", name="Bad", calculation_rule="NOT VALID JSON {{")
    events = [_make_event("u1", "click")]
    assert calculate_metric(metric, events) == 0.0


def test_calculate_metric_ratio_zero_denominator():
    """RATIO с нулевым знаменателем → 0 (не деление на 0)."""
    metric = Metric(
        key="r",
        name="R",
        calculation_rule='{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"click"},"denominator":{"type":"COUNT","event_type_key":"purchase"}}',
    )
    events = [_make_event("u1", "click")]
    assert calculate_metric(metric, events) == 0.0
