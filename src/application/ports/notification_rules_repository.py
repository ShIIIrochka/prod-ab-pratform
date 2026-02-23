from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.notification_rule import NotificationRule


class NotificationRulesRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, rule_id: UUID) -> NotificationRule | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, rule: NotificationRule) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self, enabled_only: bool = False
    ) -> list[NotificationRule]:
        raise NotImplementedError

    @abstractmethod
    async def get_matching(
        self,
        event_type: str,
        entity_id: UUID,
        payload: dict,
    ) -> list[NotificationRule]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, rule_id: UUID) -> None:
        raise NotImplementedError
