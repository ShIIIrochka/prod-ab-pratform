from uuid import UUID

from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.domain.exceptions.notifications import ChannelConfigNotFoundError
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)


class DeleteChannelConfigUseCase:
    def __init__(
        self, repository: NotificationChannelConfigsRepositoryPort
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        config_id: UUID,
        expected_type: NotificationChannelType | None = None,
    ) -> None:
        config = await self._repository.get_by_id(config_id)
        if config is None:
            raise ChannelConfigNotFoundError()
        if expected_type is not None and config.type != expected_type:
            raise ChannelConfigNotFoundError()
        await self._repository.delete(config_id)
