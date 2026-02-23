from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
    new_notification_channel_config,
)
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)


class CreateChannelConfigUseCase:
    def __init__(
        self, repository: NotificationChannelConfigsRepositoryPort
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        type: NotificationChannelType,
        name: str,
        webhook_url: str,
        enabled: bool = True,
    ) -> NotificationChannelConfig:
        config = new_notification_channel_config(
            type=type,
            name=name,
            webhook_url=webhook_url,
            enabled=enabled,
        )
        await self._repository.save(config)
        return config
