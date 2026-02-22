"""Unit tests for RedisMetricAggregator with fakeredis (no mocks)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fakeredis import FakeAsyncRedis

from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.aggregates.metric import Metric
from src.infra.adapters.services.redis_metric_aggregator import (
    _OP_INCR,
    _OP_ZADD,
    RedisMetricAggregator,
    _bucket_min,
    _collect_update_ops,
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_event(
    event_type_key: str,
    props: dict | None = None,
    *,
    timestamp: datetime | None = None,
) -> Event:
    """Event timestamp defaults to ~30s ago so it falls in get_value's 1-min window."""
    ts = timestamp or (datetime.now(UTC) - timedelta(seconds=30))
    return Event(
        id=uuid4(),
        event_type_key=event_type_key,
        decision_id=uuid4(),
        subject_id="user-1",
        timestamp=ts,
        props=props or {},
        attribution_status=AttributionStatus.ATTRIBUTED,
    )


def _make_metric(rule: str) -> Metric:
    return Metric(
        key="test_metric",
        name="Test",
        calculation_rule=rule,
    )


@pytest.fixture
async def redis_client() -> FakeAsyncRedis:
    client = FakeAsyncRedis()
    yield client
    await client.aclose()


# ── bucket_min ─────────────────────────────────────────────────────────────────


def test_bucket_min_is_integer() -> None:
    ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    bucket = _bucket_min(ts)
    assert isinstance(bucket, int)
    assert bucket > 0


def test_bucket_min_minute_granularity() -> None:
    ts1 = datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC)
    ts2 = datetime(2026, 1, 1, 12, 5, 59, tzinfo=UTC)
    ts3 = datetime(2026, 1, 1, 12, 6, 0, tzinfo=UTC)
    assert _bucket_min(ts1) == _bucket_min(ts2)
    assert _bucket_min(ts1) != _bucket_min(ts3)


# ── _collect_update_ops ────────────────────────────────────────────────────────


def test_count_matching_event() -> None:
    rule = {"type": "COUNT", "event_type_key": "conversion"}
    event = _make_event("conversion")
    ops = _collect_update_ops(rule, event)
    assert len(ops) == 1
    suffix, value, op_type = ops[0]
    assert suffix == "c:conversion"
    assert value == 1.0
    assert op_type == _OP_INCR


def test_count_non_matching_event() -> None:
    rule = {"type": "COUNT", "event_type_key": "conversion"}
    event = _make_event("exposure")
    ops = _collect_update_ops(rule, event)
    assert ops == []


def test_sum_matching_event_with_prop() -> None:
    rule = {
        "type": "SUM",
        "event_type_key": "latency",
        "property": "duration_ms",
    }
    event = _make_event("latency", {"duration_ms": 150})
    ops = _collect_update_ops(rule, event)
    suffixes = {op[0] for op in ops}
    assert "s:latency:duration_ms" in suffixes
    assert "cp:latency:duration_ms" in suffixes


def test_sum_missing_prop_no_ops() -> None:
    rule = {
        "type": "SUM",
        "event_type_key": "latency",
        "property": "duration_ms",
    }
    event = _make_event("latency", {})
    ops = _collect_update_ops(rule, event)
    assert ops == []


def test_percentile_sorted_set() -> None:
    rule = {
        "type": "PERCENTILE",
        "event_type_key": "latency",
        "property": "duration_ms",
        "percentile": 95,
    }
    event = _make_event("latency", {"duration_ms": 300})
    ops = _collect_update_ops(rule, event)
    assert len(ops) == 1
    suffix, value, op_type = ops[0]
    assert op_type == _OP_ZADD
    assert value == 300.0


def test_ratio_collects_both_sides() -> None:
    rule = {
        "type": "RATIO",
        "numerator": {"type": "COUNT", "event_type_key": "error"},
        "denominator": {"type": "COUNT", "event_type_key": "request"},
    }
    event_error = _make_event("error")
    event_request = _make_event("request")

    ops_error = _collect_update_ops(rule, event_error)
    ops_request = _collect_update_ops(rule, event_request)

    assert any("c:error" in op[0] for op in ops_error)
    assert any("c:request" in op[0] for op in ops_request)


# ── RedisMetricAggregator.update (with FakeAsyncRedis) ─────────────────────────


@pytest.mark.asyncio
async def test_update_count_calls_incrbyfloat(
    redis_client: FakeAsyncRedis,
) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')
    event = _make_event("conversion")
    exp_id = uuid4()

    await aggregator.update(
        experiment_id=exp_id,
        event=event,
        metrics=[metric],
        max_ttl_seconds=600,
    )

    value = await aggregator.get_value(
        experiment_id=exp_id,
        metric=metric,
        window_minutes=1,
    )
    assert value == 1.0


@pytest.mark.asyncio
async def test_update_non_matching_event_no_ops(
    redis_client: FakeAsyncRedis,
) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')
    event = _make_event("exposure")
    exp_id = uuid4()

    await aggregator.update(
        experiment_id=exp_id,
        event=event,
        metrics=[metric],
        max_ttl_seconds=600,
    )

    value = await aggregator.get_value(
        experiment_id=exp_id,
        metric=metric,
        window_minutes=1,
    )
    assert value == 0.0


@pytest.mark.asyncio
async def test_update_invalid_rule_skips_gracefully(
    redis_client: FakeAsyncRedis,
) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    metric = _make_metric("not-valid-json{{{")
    event = _make_event("conversion")

    await aggregator.update(
        experiment_id=uuid4(),
        event=event,
        metrics=[metric],
        max_ttl_seconds=600,
    )


# ── RedisMetricAggregator.get_value (with FakeAsyncRedis) ──────────────────────


@pytest.mark.asyncio
async def test_get_value_count_sums_buckets(
    redis_client: FakeAsyncRedis,
) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')
    exp_id = uuid4()

    for _ in range(5):
        await aggregator.update(
            experiment_id=exp_id,
            event=_make_event("conversion"),
            metrics=[metric],
            max_ttl_seconds=600,
        )
    for _ in range(3):
        await aggregator.update(
            experiment_id=exp_id,
            event=_make_event("conversion"),  # same event type
            metrics=[metric],
            max_ttl_seconds=600,
        )

    value = await aggregator.get_value(
        experiment_id=exp_id,
        metric=metric,
        window_minutes=1,
    )
    assert value == 8.0


@pytest.mark.asyncio
async def test_get_value_count_empty_buckets_returns_zero(
    redis_client: FakeAsyncRedis,
) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')

    value = await aggregator.get_value(
        experiment_id=uuid4(),
        metric=metric,
        window_minutes=1,
    )
    assert value == 0.0


@pytest.mark.asyncio
async def test_get_value_ratio(redis_client: FakeAsyncRedis) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    rule = (
        '{"type":"RATIO",'
        '"numerator":{"type":"COUNT","event_type_key":"error"},'
        '"denominator":{"type":"COUNT","event_type_key":"request"}}'
    )
    metric = _make_metric(rule)
    exp_id = uuid4()

    for _ in range(10):
        await aggregator.update(
            experiment_id=exp_id,
            event=_make_event("error"),
            metrics=[metric],
            max_ttl_seconds=600,
        )
    for _ in range(100):
        await aggregator.update(
            experiment_id=exp_id,
            event=_make_event("request"),
            metrics=[metric],
            max_ttl_seconds=600,
        )

    value = await aggregator.get_value(
        experiment_id=exp_id,
        metric=metric,
        window_minutes=1,
    )
    assert abs(value - 0.1) < 1e-9


@pytest.mark.asyncio
async def test_get_value_percentile(redis_client: FakeAsyncRedis) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    rule = (
        '{"type":"PERCENTILE","event_type_key":"latency",'
        '"property":"duration_ms","percentile":50}'
    )
    metric = _make_metric(rule)
    exp_id = uuid4()

    for val in [100, 200, 300]:
        await aggregator.update(
            experiment_id=exp_id,
            event=_make_event("latency", {"duration_ms": val}),
            metrics=[metric],
            max_ttl_seconds=600,
        )

    value = await aggregator.get_value(
        experiment_id=exp_id,
        metric=metric,
        window_minutes=1,
    )
    assert value == 200.0


@pytest.mark.asyncio
async def test_get_value_avg(redis_client: FakeAsyncRedis) -> None:
    aggregator = RedisMetricAggregator(redis=redis_client)
    rule = '{"type":"AVG","event_type_key":"latency","property":"duration_ms"}'
    metric = _make_metric(rule)
    exp_id = uuid4()

    for val in [100.0, 200.0, 300.0]:
        await aggregator.update(
            experiment_id=exp_id,
            event=_make_event("latency", {"duration_ms": val}),
            metrics=[metric],
            max_ttl_seconds=600,
        )

    value = await aggregator.get_value(
        experiment_id=exp_id,
        metric=metric,
        window_minutes=1,
    )
    assert abs(value - 200.0) < 1e-9
