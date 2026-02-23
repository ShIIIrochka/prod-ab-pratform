from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
)
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)


class NotificationChannelConfigModel(Model):
    id = fields.UUIDField(pk=True, generate=True)
    type = fields.CharField(max_length=50)
    name = fields.CharField(max_length=255)
    webhook_url = fields.TextField()
    enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notification_channel_configs"

    def to_domain(self) -> NotificationChannelConfig:
        return NotificationChannelConfig(
            id=self.id,
            type=NotificationChannelType(self.type),
            name=self.name,
            webhook_url=self.webhook_url,
            enabled=self.enabled,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(
        cls, config: NotificationChannelConfig
    ) -> NotificationChannelConfigModel:
        return cls(
            id=config.id,
            type=config.type.value,
            name=config.name,
            webhook_url=config.webhook_url,
            enabled=config.enabled,
            created_at=config.created_at,
        )
