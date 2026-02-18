from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from src.domain.aggregates.event import AttributionStatus, Event


class EventModel(Model):
    id = fields.UUIDField(pk=True)
    event_type_key = fields.CharField(max_length=255, index=True)
    decision_id = fields.CharField(max_length=36, index=True)
    subject_id = fields.CharField(max_length=255, index=True)
    timestamp = fields.DatetimeField(index=True)

    props = fields.JSONField(default=dict, description="Event properties")

    attribution_status = fields.CharField(
        max_length=50,
        default="pending",
        description="AttributionStatus enum: pending, attributed, rejected",
    )

    class Meta:
        table = "events"
        indexes = [
            # Критично для атрибуции и отчётов
            ("decision_id", "event_type_key"),
            ("subject_id", "timestamp"),
            ("event_type_key", "timestamp"),
        ]

    def to_domain(self) -> Event:
        """Преобразование Tortoise модели в доменный агрегат."""
        return Event(
            id=self.id,
            event_type_key=self.event_type_key,
            decision_id=self.decision_id,
            subject_id=self.subject_id,
            timestamp=self.timestamp,
            props=self.props,
            attribution_status=AttributionStatus(self.attribution_status),
        )

    @classmethod
    def from_domain(cls, event: Event) -> EventModel:
        """Преобразование доменного агрегата в Tortoise модель."""
        return cls(
            id=event.id,
            event_type_key=event.event_type_key,
            decision_id=event.decision_id,
            subject_id=event.subject_id,
            timestamp=event.timestamp,
            props=event.props,
            attribution_status=event.attribution_status.value,
        )
