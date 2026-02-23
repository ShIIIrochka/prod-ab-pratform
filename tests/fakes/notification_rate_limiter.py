from uuid import UUID

from src.application.ports.notification_rate_limiter import (
    NotificationRateLimiterPort,
)


class FakeNotificationRateLimiter(NotificationRateLimiterPort):
    """Always allows unless explicitly blocked for a (rule_id, entity_id) pair."""

    def __init__(self) -> None:
        self._blocked: set[tuple[UUID, UUID]] = set()
        self.calls: list[dict] = []

    def block(self, rule_id: UUID, entity_id: UUID) -> None:
        self._blocked.add((rule_id, entity_id))

    async def is_allowed(
        self,
        rule_id: UUID,
        entity_id: UUID,
        event_type: str,
        rate_limit_seconds: int,
    ) -> bool:
        self.calls.append(
            {
                "rule_id": rule_id,
                "entity_id": entity_id,
                "event_type": event_type,
                "rate_limit_seconds": rate_limit_seconds,
            }
        )
        if rate_limit_seconds <= 0:
            return True
        return (rule_id, entity_id) not in self._blocked
