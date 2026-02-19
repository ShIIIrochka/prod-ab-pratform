"""Redis-based инкрементальный агрегатор метрик для guardrails.

Схема ключей (минутные buckets, TTL = max_ttl_seconds):
  COUNT  → aggr:{exp_id}:{metric_key}:{bucket_min}:c:{event_type}
  SUM    → aggr:{exp_id}:{metric_key}:{bucket_min}:s:{event_type}:{prop}
  AVG    → sum: aggr:...s:..., count: aggr:...cp:{event_type}:{prop}
  RATIO  → рекурсивно по sub-rule numerator/denominator
  PCTL   → aggr:{exp_id}:{metric_key}:{bucket_min}:z:{event_type}:{prop}  (Sorted Set)

calculation_rule поддерживает JSON и DSL форматы (см. calculation_rule_parser).
При чтении агрегируем все buckets в окне window_minutes, вычисляем итоговое
значение по формуле из calculation_rule — без единого SQL-запроса.
"""

from __future__ import annotations

import logging

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from src.application.ports.metric_aggregator import MetricAggregatorPort
from src.domain.aggregates.event import Event
from src.domain.aggregates.metric import Metric
from src.domain.services.calculation_rule_parser import parse_calculation_rule


logger = logging.getLogger(__name__)

_PREFIX = "aggr"


def _bucket_min(ts: datetime) -> int:
    """Возвращает номер минутного bucket для метки времени."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return int(ts.timestamp() / 60)


def _collect_update_ops(
    rule: dict[str, Any], event: Event
) -> list[tuple[str, float, bool]]:
    """Возвращает список (key_suffix, value, is_sorted_set) для обновления.

    key_suffix — суффикс после base_key без ведущего ':'
    value      — значение для INCRBYFLOAT или score для ZADD
    is_sorted_set — True для PERCENTILE, иначе False (INCRBYFLOAT)
    """
    rule_type = rule.get("type", "").upper()
    event_type_key = rule.get("event_type_key", "")

    if rule_type == "COUNT":
        if not event_type_key or event.event_type_key != event_type_key:
            return []
        return [(f"c:{event_type_key}", 1.0, False)]

    if rule_type in ("SUM", "AVG"):
        prop = rule.get("property", "")
        if not event_type_key or not prop:
            return []
        if event.event_type_key != event_type_key:
            return []
        raw = event.props.get(prop)
        if raw is None:
            return []
        try:
            fval = float(raw)
        except (TypeError, ValueError):
            return []
        return [
            (f"s:{event_type_key}:{prop}", fval, False),
            (f"cp:{event_type_key}:{prop}", 1.0, False),
        ]

    if rule_type == "PERCENTILE":
        prop = rule.get("property", "")
        if not event_type_key or not prop:
            return []
        if event.event_type_key != event_type_key:
            return []
        raw = event.props.get(prop)
        if raw is None:
            return []
        try:
            fval = float(raw)
        except (TypeError, ValueError):
            return []
        return [(f"z:{event_type_key}:{prop}", fval, True)]

    if rule_type == "RATIO":
        ops: list[tuple[str, float, bool]] = []
        num_rule = rule.get("numerator")
        den_rule = rule.get("denominator")
        if num_rule:
            ops.extend(_collect_update_ops(num_rule, event))
        if den_rule:
            ops.extend(_collect_update_ops(den_rule, event))
        return ops

    return []


async def _eval_rule(
    rule: dict[str, Any],
    redis: Redis,
    base: str,
    buckets: list[int],
) -> float:
    """Вычисляет значение правила по агрегированным bucket-значениям."""
    rule_type = rule.get("type", "").upper()
    event_type_key = rule.get("event_type_key", "")
    prop = rule.get("property", "")

    if rule_type == "COUNT":
        keys = [f"{base}:{b}:c:{event_type_key}" for b in buckets]
        values = await redis.mget(keys)
        return sum(float(v) for v in values if v is not None)

    if rule_type == "SUM":
        keys = [f"{base}:{b}:s:{event_type_key}:{prop}" for b in buckets]
        values = await redis.mget(keys)
        return sum(float(v) for v in values if v is not None)

    if rule_type == "AVG":
        sum_keys = [f"{base}:{b}:s:{event_type_key}:{prop}" for b in buckets]
        cnt_keys = [f"{base}:{b}:cp:{event_type_key}:{prop}" for b in buckets]
        sum_vals = await redis.mget(sum_keys)
        cnt_vals = await redis.mget(cnt_keys)
        total_sum = sum(float(v) for v in sum_vals if v is not None)
        total_cnt = sum(float(v) for v in cnt_vals if v is not None)
        return total_sum / total_cnt if total_cnt > 0 else 0.0

    if rule_type == "PERCENTILE":
        percentile = rule.get("percentile", 95)
        all_values: list[float] = []
        for b in buckets:
            key = f"{base}:{b}:z:{event_type_key}:{prop}"
            entries = await redis.zrange(key, 0, -1, withscores=True)
            all_values.extend(score for _, score in entries)
        if not all_values:
            return 0.0
        sorted_vals = sorted(all_values)
        idx = min(
            int(len(sorted_vals) * percentile / 100),
            len(sorted_vals) - 1,
        )
        return sorted_vals[idx]

    if rule_type == "RATIO":
        num_rule = rule.get("numerator")
        den_rule = rule.get("denominator")
        if not num_rule or not den_rule:
            return 0.0
        numerator = await _eval_rule(num_rule, redis, base, buckets)
        denominator = await _eval_rule(den_rule, redis, base, buckets)
        return numerator / denominator if denominator != 0 else 0.0

    return 0.0


class RedisMetricAggregator(MetricAggregatorPort):
    def __init__(self, redis: Redis, default_ttl_seconds: int = 3600) -> None:
        self._redis = redis
        self._default_ttl = default_ttl_seconds

    async def update(
        self,
        experiment_id: UUID,
        event: Event,
        metrics: list[Metric],
        max_ttl_seconds: int,
    ) -> None:
        bucket = _bucket_min(event.timestamp)
        ttl = max(max_ttl_seconds, self._default_ttl)

        pipeline = self._redis.pipeline()

        for metric in metrics:
            rule = parse_calculation_rule(metric.calculation_rule)
            if rule is None:
                logger.warning(
                    "Invalid or empty calculation_rule for metric %s, skipping",
                    metric.key,
                )
                continue

            base = f"{_PREFIX}:{experiment_id}:{metric.key}:{bucket}"
            ops = _collect_update_ops(rule, event)

            for suffix, value, is_sorted_set in ops:
                key = f"{base}:{suffix}"
                if is_sorted_set:
                    pipeline.zadd(key, {str(event.id): value})
                else:
                    pipeline.incrbyfloat(key, value)
                pipeline.expire(key, ttl)

        await pipeline.execute()

    async def get_value(
        self,
        experiment_id: UUID,
        metric: Metric,
        window_minutes: int,
    ) -> float:
        rule = parse_calculation_rule(metric.calculation_rule)
        if rule is None:
            logger.warning(
                "Invalid or empty calculation_rule for metric %s, returning 0.0",
                metric.key,
            )
            return 0.0

        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=window_minutes)
        start_bucket = _bucket_min(window_start)
        end_bucket = _bucket_min(now)
        buckets = list(range(start_bucket, end_bucket + 1))

        base = f"{_PREFIX}:{experiment_id}:{metric.key}"

        try:
            return await _eval_rule(rule, self._redis, base, buckets)
        except Exception as exc:
            logger.warning(
                "Error computing metric %s from Redis: %s", metric.key, exc
            )
            return 0.0
