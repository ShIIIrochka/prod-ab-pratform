from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.aggregates import BaseEntity


@dataclass
class NotificationRule(BaseEntity):
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
    created_at: datetime = field(default_factory=datetime.utcnow)

    def matches(self, event_type: str, entity_id: UUID, payload: dict) -> bool:  # noqa: ARG002
        if not self.enabled:
            return False
        if self.event_type != event_type and self.event_type != "*":
            return False
        if self.experiment_id is not None and self.experiment_id != entity_id:
            return False
        if self.flag_key is not None:
            if payload.get("flag_key") != self.flag_key:
                return False
        if self.owner_id is not None:
            if payload.get("owner_id") != self.owner_id:
                return False
        if self.metric_key is not None:
            if payload.get("metric_key") != self.metric_key:
                return False
        return True


def new_notification_rule(
    event_type: str,
    channel_config_id: UUID,
    enabled: bool = True,
    experiment_id: UUID | None = None,
    flag_key: str | None = None,
    owner_id: str | None = None,
    metric_key: str | None = None,
    severity: str | None = None,
    rate_limit_seconds: int = 0,
    template: str | None = None,
) -> NotificationRule:
    return NotificationRule(
        id=uuid4(),
        event_type=event_type,
        channel_config_id=channel_config_id,
        enabled=enabled,
        experiment_id=experiment_id,
        flag_key=flag_key,
        owner_id=owner_id,
        metric_key=metric_key,
        severity=severity,
        rate_limit_seconds=rate_limit_seconds,
        template=template,
    )
