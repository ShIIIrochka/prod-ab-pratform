from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)
from src.domain.value_objects.notification_delivery_status import (
    NotificationDeliveryStatus,
)


class CreateChannelConfigRequest(BaseModel):
    type: NotificationChannelType
    name: str
    webhook_url: str
    enabled: bool = True


class ChannelConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: NotificationChannelType
    name: str
    webhook_url: str
    enabled: bool
    created_at: datetime


class CreateNotificationRuleRequest(BaseModel):
    event_type: str
    channel_config_id: UUID
    enabled: bool = True
    experiment_id: UUID | None = None
    flag_key: str | None = None
    owner_id: str | None = None
    metric_key: str | None = None
    severity: str | None = None
    rate_limit_seconds: int = 0
    template: str | None = None


class UpdateNotificationRuleRequest(BaseModel):
    enabled: bool | None = None
    rate_limit_seconds: int | None = None
    template: str | None = None


class NotificationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    channel_config_id: UUID
    enabled: bool
    experiment_id: UUID | None
    flag_key: str | None
    owner_id: str | None
    metric_key: str | None
    severity: str | None
    rate_limit_seconds: int
    template: str | None
    created_at: datetime


class NotificationDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    rule_id: UUID
    channel_config_id: UUID
    status: NotificationDeliveryStatus
    attempt_count: int
    last_error: str | None
    sent_at: datetime | None
    created_at: datetime
