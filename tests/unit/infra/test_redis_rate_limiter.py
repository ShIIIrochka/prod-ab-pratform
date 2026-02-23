"""Unit tests for RedisNotificationRateLimiter."""

from __future__ import annotations

from uuid import uuid4

import fakeredis.aioredis as fakeredis
import pytest

from src.infra.adapters.services.redis_notification_rate_limiter import (
    RedisNotificationRateLimiter,
)


pytestmark = pytest.mark.asyncio


async def test_first_call_is_allowed() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisNotificationRateLimiter(redis=redis)

    result = await limiter.is_allowed(
        uuid4(), uuid4(), "experiment.launched", 60
    )
    assert result is True


async def test_second_call_within_window_is_blocked() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisNotificationRateLimiter(redis=redis)

    rule_id = uuid4()
    entity_id = uuid4()

    first = await limiter.is_allowed(
        rule_id, entity_id, "experiment.launched", 60
    )
    second = await limiter.is_allowed(
        rule_id, entity_id, "experiment.launched", 60
    )

    assert first is True
    assert second is False


async def test_zero_rate_limit_always_allowed() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisNotificationRateLimiter(redis=redis)

    rule_id = uuid4()
    entity_id = uuid4()

    for _ in range(5):
        result = await limiter.is_allowed(
            rule_id, entity_id, "experiment.launched", 0
        )
        assert result is True


async def test_different_rules_are_independent() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisNotificationRateLimiter(redis=redis)

    entity_id = uuid4()
    rule1 = uuid4()
    rule2 = uuid4()

    await limiter.is_allowed(rule1, entity_id, "experiment.launched", 60)
    # rule2 should still be allowed
    result = await limiter.is_allowed(
        rule2, entity_id, "experiment.launched", 60
    )
    assert result is True


async def test_different_entity_ids_are_independent() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisNotificationRateLimiter(redis=redis)

    rule_id = uuid4()
    entity1 = uuid4()
    entity2 = uuid4()

    await limiter.is_allowed(rule_id, entity1, "experiment.launched", 60)
    result = await limiter.is_allowed(
        rule_id, entity2, "experiment.launched", 60
    )
    assert result is True


async def test_different_event_types_are_independent() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisNotificationRateLimiter(redis=redis)

    rule_id = uuid4()
    entity_id = uuid4()

    await limiter.is_allowed(rule_id, entity_id, "experiment.launched", 60)
    result = await limiter.is_allowed(
        rule_id, entity_id, "guardrail.triggered", 60
    )
    assert result is True
