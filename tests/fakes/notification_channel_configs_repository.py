from uuid import UUID

from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
)


class FakeNotificationChannelConfigsRepository(
    NotificationChannelConfigsRepositoryPort
):
    def __init__(self) -> None:
        self._store: dict[UUID, NotificationChannelConfig] = {}

    async def save(self, config: NotificationChannelConfig) -> None:
        self._store[config.id] = config

    async def get_by_id(
        self, config_id: UUID
    ) -> NotificationChannelConfig | None:
        return self._store.get(config_id)

    async def list_all(
        self, enabled_only: bool = False
    ) -> list[NotificationChannelConfig]:
        configs = list(self._store.values())
        if enabled_only:
            configs = [c for c in configs if c.enabled]
        return configs

    async def delete(self, config_id: UUID) -> None:
        self._store.pop(config_id, None)
