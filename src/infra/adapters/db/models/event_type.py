from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from src.domain.aggregates.event_type import EventType


class EventTypeModel(Model):
    id = fields.UUIDField(pk=True)
    key = fields.CharField(
        max_length=255,
        unique=True,
        index=True,
    )
    name = fields.CharField(max_length=511)
    description = fields.TextField(null=True)
    required_params = fields.JSONField(default=dict)
    requires_exposure = fields.BooleanField(default=False)

    class Meta:
        table = "event_types"

    def to_domain(self) -> EventType:
        """Преобразование Tortoise модели в доменный агрегат."""
        return EventType(
            id=self.id,
            key=self.key,
            name=self.name,
            description=self.description,
            required_params=self.required_params,
            requires_exposure=self.requires_exposure,
        )

    @classmethod
    def from_domain(cls, event_type: EventType) -> EventTypeModel:
        """Преобразование доменного агрегата в Tortoise модель."""
        return cls(
            id=event_type.id,
            key=event_type.key,
            name=event_type.name,
            description=event_type.description,
            required_params=event_type.required_params,
            requires_exposure=event_type.requires_exposure,
        )
