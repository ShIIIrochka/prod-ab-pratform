from __future__ import annotations

from uuid import UUID

from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
)
from src.infra.adapters.db.models.notification_channel_config import (
    NotificationChannelConfigModel,
)


class NotificationChannelConfigsRepository(
    NotificationChannelConfigsRepositoryPort
):
    async def save(self, config: NotificationChannelConfig) -> None:
        existing = await NotificationChannelConfigModel.get_or_none(
            id=config.id
        )
        model = NotificationChannelConfigModel.from_domain(config)
        if existing:
            await model.save(force_update=True)
        else:
            await model.save()

    async def get_by_id(
        self, config_id: UUID
    ) -> NotificationChannelConfig | None:
        model = await NotificationChannelConfigModel.get_or_none(id=config_id)
        return model.to_domain() if model else None

    async def list_all(
        self, enabled_only: bool = False
    ) -> list[NotificationChannelConfig]:
        q = NotificationChannelConfigModel.all()
        if enabled_only:
            q = q.filter(enabled=True)
        models = await q.order_by("created_at")
        return [m.to_domain() for m in models]

    async def delete(self, config_id: UUID) -> None:
        await NotificationChannelConfigModel.filter(id=config_id).delete()
