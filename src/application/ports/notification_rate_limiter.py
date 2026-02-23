from abc import ABC, abstractmethod
from uuid import UUID


class NotificationRateLimiterPort(ABC):
    @abstractmethod
    async def is_allowed(
        self,
        rule_id: UUID,
        entity_id: UUID,
        event_type: str,
        rate_limit_seconds: int,
    ) -> bool:
        raise NotImplementedError
