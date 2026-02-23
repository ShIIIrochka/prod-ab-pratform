from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from src.domain.value_objects.notification_event import NotificationEvent


class NotificationEventModel(Model):
    """Dedup table for notification events.

    Unique constraint on event_id ensures each domain event is processed once.
    """

    id = fields.UUIDField(pk=True)
    event_type = fields.CharField(max_length=100)
    entity_type = fields.CharField(max_length=100)
    entity_id = fields.UUIDField()
    payload = fields.JSONField()
    occurred_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notification_events"

    def to_domain(self) -> NotificationEvent:
        return NotificationEvent(
            event_id=self.id,
            event_type=self.event_type,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            payload=self.payload,
            occurred_at=self.occurred_at,
        )

    @classmethod
    def from_domain(cls, event: NotificationEvent) -> NotificationEventModel:
        return cls(
            id=event.event_id,
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            payload=event.payload,
            occurred_at=event.occurred_at,
        )
