from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class EventTypeModel(Model):
    """Tortoise модель для каталога типов событий.

    Соответствует domain.aggregates.event_type.EventType
    """

    key = fields.CharField(
        pk=True,
        max_length=255,
        description="Event type key (unique identifier)",
    )
    name = fields.CharField(max_length=500, description="Human-readable name")
    description = fields.TextField(
        null=True, description="Event type description"
    )

    # Обязательные параметры события (например, {"screen": "string", "button_id": "string"})
    required_params_json = fields.JSONField(
        default=dict, description="Required event parameters schema"
    )

    requires_exposure = fields.BooleanField(
        default=False,
        description="Whether event requires exposure for attribution",
    )

    class Meta:
        table = "event_types"
