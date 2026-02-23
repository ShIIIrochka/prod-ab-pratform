from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.domain.aggregates import BaseEntity
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)


@dataclass
class NotificationChannelConfig(BaseEntity):
    type: NotificationChannelType
    name: str
    webhook_url: str
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


def new_notification_channel_config(
    type: NotificationChannelType,
    name: str,
    webhook_url: str,
    enabled: bool = True,
) -> NotificationChannelConfig:
    return NotificationChannelConfig(
        id=uuid4(),
        type=type,
        name=name,
        webhook_url=webhook_url,
        enabled=enabled,
    )
