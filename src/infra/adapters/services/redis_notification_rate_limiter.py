from uuid import UUID

from redis.asyncio import Redis

from src.application.ports.notification_rate_limiter import (
    NotificationRateLimiterPort,
)


class RedisNotificationRateLimiter(NotificationRateLimiterPort):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def is_allowed(
        self,
        rule_id: UUID,
        entity_id: UUID,
        event_type: str,
        rate_limit_seconds: int,
    ) -> bool:
        if rate_limit_seconds <= 0:
            return True
        key = f"notif:rl:{rule_id}:{entity_id}:{event_type}"
        result = await self._redis.set(key, "1", nx=True, ex=rate_limit_seconds)
        return result is not None
