from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.entities.notification_rule import NotificationRule


class NotificationRuleModel(Model):
    id = fields.UUIDField(pk=True, generate=True)
    event_type = fields.CharField(max_length=100)
    channel_config = fields.ForeignKeyField(
        "models.NotificationChannelConfigModel",
        related_name="rules",
        on_delete=OnDelete.CASCADE,
    )
    enabled = fields.BooleanField(default=True)
    # Optional scope/filter fields
    experiment_id = fields.UUIDField(null=True)
    flag_key = fields.CharField(max_length=255, null=True)
    owner_id = fields.CharField(max_length=255, null=True)
    metric_key = fields.CharField(max_length=255, null=True)
    severity = fields.CharField(max_length=50, null=True)
    rate_limit_seconds = fields.IntField(default=0)
    template = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notification_rules"
        indexes = [
            ("event_type", "enabled"),
        ]

    def to_domain(self) -> NotificationRule:
        return NotificationRule(
            id=self.id,
            event_type=self.event_type,
            channel_config_id=self.channel_config_id,  # type: ignore[arg-type]
            enabled=self.enabled,
            experiment_id=self.experiment_id,
            flag_key=self.flag_key,
            owner_id=self.owner_id,
            metric_key=self.metric_key,
            severity=self.severity,
            rate_limit_seconds=self.rate_limit_seconds,
            template=self.template,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, rule: NotificationRule) -> NotificationRuleModel:
        return cls(
            id=rule.id,
            event_type=rule.event_type,
            channel_config_id=rule.channel_config_id,
            enabled=rule.enabled,
            experiment_id=rule.experiment_id,
            flag_key=rule.flag_key,
            owner_id=rule.owner_id,
            metric_key=rule.metric_key,
            severity=rule.severity,
            rate_limit_seconds=rule.rate_limit_seconds,
            template=rule.template,
            created_at=rule.created_at,
        )
