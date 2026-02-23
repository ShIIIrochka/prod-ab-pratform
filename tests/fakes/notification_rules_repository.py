from uuid import UUID

from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.domain.entities.notification_rule import NotificationRule


class FakeNotificationRulesRepository(NotificationRulesRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[UUID, NotificationRule] = {}

    async def save(self, rule: NotificationRule) -> None:
        self._store[rule.id] = rule

    async def get_by_id(self, rule_id: UUID) -> NotificationRule | None:
        return self._store.get(rule_id)

    async def list_all(
        self, enabled_only: bool = False
    ) -> list[NotificationRule]:
        rules = list(self._store.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    async def get_matching(
        self, event_type: str, entity_id: UUID, payload: dict
    ) -> list[NotificationRule]:
        return [
            r
            for r in self._store.values()
            if r.matches(event_type, entity_id, payload)
        ]

    async def delete(self, rule_id: UUID) -> None:
        self._store.pop(rule_id, None)
