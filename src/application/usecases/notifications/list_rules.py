from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.domain.entities.notification_rule import NotificationRule


class ListNotificationRulesUseCase:
    def __init__(self, repository: NotificationRulesRepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self, enabled_only: bool = False
    ) -> list[NotificationRule]:
        return await self._repository.list_all(enabled_only=enabled_only)
