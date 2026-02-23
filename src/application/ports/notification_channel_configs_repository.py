from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
)


class NotificationChannelConfigsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, config: NotificationChannelConfig) -> None: ...

    @abstractmethod
    async def get_by_id(
        self, config_id: UUID
    ) -> NotificationChannelConfig | None: ...

    @abstractmethod
    async def list_all(
        self, enabled_only: bool = False
    ) -> list[NotificationChannelConfig]: ...

    @abstractmethod
    async def delete(self, config_id: UUID) -> None: ...
