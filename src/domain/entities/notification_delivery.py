from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.aggregates import BaseEntity
from src.domain.value_objects.notification_delivery_status import (
    NotificationDeliveryStatus,
)


@dataclass
class NotificationDelivery(BaseEntity):
    event_id: UUID
    rule_id: UUID
    channel_config_id: UUID
    status: NotificationDeliveryStatus
    attempt_count: int = 0
    last_error: str | None = None
    sent_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def mark_sent(self) -> None:
        self.status = NotificationDeliveryStatus.SENT
        self.sent_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = NotificationDeliveryStatus.FAILED
        self.last_error = error
        self.attempt_count += 1

    def mark_permanent_failed(self, error: str) -> None:
        self.status = NotificationDeliveryStatus.PERMANENT_FAILED
        self.last_error = error
        self.attempt_count += 1

    def mark_rate_limited(self) -> None:
        self.status = NotificationDeliveryStatus.SKIPPED_RATE_LIMITED


def new_notification_delivery(
    event_id: UUID,
    rule_id: UUID,
    channel_config_id: UUID,
) -> NotificationDelivery:
    return NotificationDelivery(
        id=uuid4(),
        event_id=event_id,
        rule_id=rule_id,
        channel_config_id=channel_config_id,
        status=NotificationDeliveryStatus.PENDING,
    )
