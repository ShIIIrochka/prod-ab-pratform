from uuid import UUID

from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.domain.entities.notification_rule import NotificationRule


class UpdateNotificationRuleUseCase:
    def __init__(self, repository: NotificationRulesRepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self,
        rule_id: UUID,
        enabled: bool | None = None,
        rate_limit_seconds: int | None = None,
        template: str | None = None,
    ) -> NotificationRule:
        rule = await self._repository.get_by_id(rule_id)
        if rule is None:
            msg = f"Notification rule {rule_id} not found"
            raise ValueError(msg)

        if enabled is not None:
            rule.enabled = enabled
        if rate_limit_seconds is not None:
            rule.rate_limit_seconds = rate_limit_seconds
        if template is not None:
            rule.template = template

        await self._repository.save(rule)
        return rule
