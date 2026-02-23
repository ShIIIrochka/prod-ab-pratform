from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
)


class ListChannelConfigsUseCase:
    def __init__(
        self, repository: NotificationChannelConfigsRepositoryPort
    ) -> None:
        self._repository = repository

    async def execute(
        self, enabled_only: bool = False
    ) -> list[NotificationChannelConfig]:
        return await self._repository.list_all(enabled_only=enabled_only)
