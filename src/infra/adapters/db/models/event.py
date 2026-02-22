from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.aggregates.event import AttributionStatus, Event


class EventModel(Model):
    id = fields.UUIDField(pk=True)
    event_type_key = fields.CharField(max_length=255, index=True)
    decision = fields.ForeignKeyField(
        "models.DecisionModel",
        related_name="events",
        on_delete=OnDelete.RESTRICT,
    )
    subject = fields.ForeignKeyField(
        "models.UserModel",
        related_name="events",
        on_delete=OnDelete.RESTRICT,
    )
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
            ("decision_id", "event_type_key"),
            ("subject_id", "timestamp"),
            ("event_type_key", "timestamp"),
        ]

    def to_domain(self) -> Event:
        return Event(
            id=self.id,
            event_type_key=self.event_type_key,
            decision_id=self.decision_id,  # type: ignore[arg-type]
            subject_id=self.subject_id,  # type: ignore[arg-type]
            timestamp=self.timestamp,
            props=self.props,
            attribution_status=AttributionStatus(self.attribution_status),
        )

    @classmethod
    def from_domain(cls, event: Event) -> EventModel:
        return cls(
            id=event.id,
            event_type_key=event.event_type_key,
            decision_id=event.decision_id,
            subject_id=event.subject_id,
            timestamp=event.timestamp,
            props=event.props,
            attribution_status=event.attribution_status.value,
        )
