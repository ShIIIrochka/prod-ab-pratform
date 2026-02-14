from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class EventModel(Model):
    """Tortoise модель для событий.

    Соответствует domain.aggregates.event.Event
    """

    id = fields.CharField(
        pk=True, max_length=255, description="Event ID (unique)"
    )
    event_type_key = fields.CharField(
        max_length=255, index=True, description="Event type key"
    )
    decision_id = fields.CharField(
        max_length=36, index=True, description="Decision UUID for attribution"
    )
    subject_id = fields.CharField(
        max_length=255, index=True, description="Subject identifier"
    )
    timestamp = fields.DatetimeField(index=True, description="Event timestamp")

    # Дополнительные параметры события
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
