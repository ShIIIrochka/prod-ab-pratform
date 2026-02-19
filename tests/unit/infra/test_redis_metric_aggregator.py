"""Unit tests for RedisMetricAggregator."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.aggregates.metric import Metric
from src.infra.adapters.services.redis_metric_aggregator import (
    RedisMetricAggregator,
    _bucket_min,
    _collect_update_ops,
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_event(event_type_key: str, props: dict | None = None) -> Event:
    return Event(
        id=uuid4(),
        event_type_key=event_type_key,
        decision_id="dec-1",
        subject_id="user-1",
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        props=props or {},
        attribution_status=AttributionStatus.ATTRIBUTED,
    )


def _make_metric(rule: str) -> Metric:
    return Metric(
        key="test_metric",
        name="Test",
        calculation_rule=rule,
    )


# ── bucket_min ─────────────────────────────────────────────────────────────────


def test_bucket_min_is_integer():
    ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    bucket = _bucket_min(ts)
    assert isinstance(bucket, int)
    assert bucket > 0


def test_bucket_min_minute_granularity():
    ts1 = datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC)
    ts2 = datetime(2026, 1, 1, 12, 5, 59, tzinfo=UTC)
    ts3 = datetime(2026, 1, 1, 12, 6, 0, tzinfo=UTC)
    assert _bucket_min(ts1) == _bucket_min(ts2)
    assert _bucket_min(ts1) != _bucket_min(ts3)


# ── _collect_update_ops ────────────────────────────────────────────────────────


def test_count_matching_event():
    rule = {"type": "COUNT", "event_type_key": "conversion"}
    event = _make_event("conversion")
    ops = _collect_update_ops(rule, event)
    assert len(ops) == 1
    suffix, value, is_zset = ops[0]
    assert suffix == "c:conversion"
    assert value == 1.0
    assert not is_zset


def test_count_non_matching_event():
    rule = {"type": "COUNT", "event_type_key": "conversion"}
    event = _make_event("exposure")
    ops = _collect_update_ops(rule, event)
    assert ops == []


def test_sum_matching_event_with_prop():
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


def test_sum_missing_prop_no_ops():
    rule = {
        "type": "SUM",
        "event_type_key": "latency",
        "property": "duration_ms",
    }
    event = _make_event("latency", {})  # no duration_ms
    ops = _collect_update_ops(rule, event)
    assert ops == []


def test_percentile_sorted_set():
    rule = {
        "type": "PERCENTILE",
        "event_type_key": "latency",
        "property": "duration_ms",
        "percentile": 95,
    }
    event = _make_event("latency", {"duration_ms": 300})
    ops = _collect_update_ops(rule, event)
    assert len(ops) == 1
    suffix, value, is_zset = ops[0]
    assert is_zset
    assert value == 300.0


def test_ratio_collects_both_sides():
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


# ── RedisMetricAggregator.update ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_count_calls_incrbyfloat():
    redis = AsyncMock()
    pipeline = AsyncMock()
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)

    aggregator = RedisMetricAggregator(redis=redis)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')
    event = _make_event("conversion")

    await aggregator.update(
        experiment_id=uuid4(),
        event=event,
        metrics=[metric],
        max_ttl_seconds=600,
    )
    pipeline.incrbyfloat.assert_called_once()
    pipeline.expire.assert_called_once()


@pytest.mark.asyncio
async def test_update_non_matching_event_no_ops():
    redis = AsyncMock()
    pipeline = AsyncMock()
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)

    aggregator = RedisMetricAggregator(redis=redis)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')
    event = _make_event("exposure")  # different event type

    await aggregator.update(
        experiment_id=uuid4(),
        event=event,
        metrics=[metric],
        max_ttl_seconds=600,
    )
    pipeline.incrbyfloat.assert_not_called()
    pipeline.zadd.assert_not_called()


@pytest.mark.asyncio
async def test_update_invalid_rule_skips_gracefully():
    redis = AsyncMock()
    pipeline = AsyncMock()
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)

    aggregator = RedisMetricAggregator(redis=redis)
    metric = _make_metric("not-valid-json{{{")
    event = _make_event("conversion")

    # Should not raise
    await aggregator.update(
        experiment_id=uuid4(),
        event=event,
        metrics=[metric],
        max_ttl_seconds=600,
    )


# ── RedisMetricAggregator.get_value ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_value_count_sums_buckets():
    redis = AsyncMock()
    # Return values for 2 buckets (covering ~1 min window)
    redis.mget = AsyncMock(return_value=["5", "3"])

    aggregator = RedisMetricAggregator(redis=redis)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')

    value = await aggregator.get_value(
        experiment_id=uuid4(),
        metric=metric,
        window_minutes=1,
    )
    assert value == 8.0  # 5 + 3


@pytest.mark.asyncio
async def test_get_value_count_empty_buckets_returns_zero():
    redis = AsyncMock()
    redis.mget = AsyncMock(return_value=[None, None])

    aggregator = RedisMetricAggregator(redis=redis)
    metric = _make_metric('{"type":"COUNT","event_type_key":"conversion"}')

    value = await aggregator.get_value(
        experiment_id=uuid4(),
        metric=metric,
        window_minutes=1,
    )
    assert value == 0.0


@pytest.mark.asyncio
async def test_get_value_ratio():
    redis = AsyncMock()
    # For RATIO, mget is called twice (numerator + denominator)
    call_count = 0

    async def mock_mget(keys):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ["10"]  # numerator = 10
        return ["100"]  # denominator = 100

    redis.mget = mock_mget

    aggregator = RedisMetricAggregator(redis=redis)
    rule = (
        '{"type":"RATIO",'
        '"numerator":{"type":"COUNT","event_type_key":"error"},'
        '"denominator":{"type":"COUNT","event_type_key":"request"}}'
    )
    metric = _make_metric(rule)

    value = await aggregator.get_value(
        experiment_id=uuid4(),
        metric=metric,
        window_minutes=1,
    )
    assert abs(value - 0.1) < 1e-9


@pytest.mark.asyncio
async def test_get_value_percentile():
    redis = AsyncMock()
    # Sorted set values for 1 bucket
    redis.zrange = AsyncMock(
        return_value=[("evt1", 100.0), ("evt2", 200.0), ("evt3", 300.0)]
    )

    aggregator = RedisMetricAggregator(redis=redis)
    rule = (
        '{"type":"PERCENTILE","event_type_key":"latency",'
        '"property":"duration_ms","percentile":50}'
    )
    metric = _make_metric(rule)

    value = await aggregator.get_value(
        experiment_id=uuid4(),
        metric=metric,
        window_minutes=1,
    )
    # 50th percentile of [100, 200, 300] = 200
    assert value == 200.0


@pytest.mark.asyncio
async def test_get_value_avg():
    redis = AsyncMock()
    call_count = 0

    async def mock_mget(keys):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ["600.0"]  # sum
        return ["3"]  # count

    redis.mget = mock_mget
    aggregator = RedisMetricAggregator(redis=redis)
    rule = '{"type":"AVG","event_type_key":"latency","property":"duration_ms"}'
    metric = _make_metric(rule)

    value = await aggregator.get_value(
        experiment_id=uuid4(),
        metric=metric,
        window_minutes=1,
    )
    assert abs(value - 200.0) < 1e-9
