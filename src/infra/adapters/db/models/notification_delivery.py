from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.entities.notification_delivery import NotificationDelivery
from src.domain.value_objects.notification_delivery_status import (
    NotificationDeliveryStatus,
)


class NotificationDeliveryModel(Model):
    id = fields.UUIDField(pk=True, generate=True)
    event = fields.ForeignKeyField(
        "models.NotificationEventModel",
        related_name="deliveries",
        on_delete=OnDelete.CASCADE,
    )
    rule = fields.ForeignKeyField(
        "models.NotificationRuleModel",
        related_name="deliveries",
        on_delete=OnDelete.SET_NULL,
        null=True,
    )
    channel_config = fields.ForeignKeyField(
        "models.NotificationChannelConfigModel",
        related_name="deliveries",
        on_delete=OnDelete.SET_NULL,
        null=True,
    )
    status = fields.CharField(
        max_length=50, default=NotificationDeliveryStatus.PENDING.value
    )
    attempt_count = fields.IntField(default=0)
    last_error = fields.TextField(null=True)
    sent_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notification_deliveries"
        unique_together = (("event_id", "rule_id"),)
        indexes = [
            ("event_id",),
            ("status",),
            ("created_at",),
        ]

    def to_domain(self) -> NotificationDelivery:
        return NotificationDelivery(
            id=self.id,
            event_id=self.event_id,  # type: ignore[arg-type]
            rule_id=self.rule_id,  # type: ignore[arg-type]
            channel_config_id=self.channel_config_id,  # type: ignore[arg-type]
            status=NotificationDeliveryStatus(self.status),
            attempt_count=self.attempt_count,
            last_error=self.last_error,
            sent_at=self.sent_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(
        cls, delivery: NotificationDelivery
    ) -> NotificationDeliveryModel:
        return cls(
            id=delivery.id,
            event_id=delivery.event_id,
            rule_id=delivery.rule_id,
            channel_config_id=delivery.channel_config_id,
            status=delivery.status.value,
            attempt_count=delivery.attempt_count,
            last_error=delivery.last_error,
            sent_at=delivery.sent_at,
            created_at=delivery.created_at,
        )
