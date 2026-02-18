from __future__ import annotations

from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.domain.aggregates.event_type import EventType
from src.infra.adapters.db.models.event_type import EventTypeModel


class EventTypesRepository(EventTypesRepositoryPort):
    async def save(self, event_type: EventType) -> None:
        existing_model = await EventTypeModel.get_or_none(key=event_type.key)
        model = EventTypeModel.from_domain(event_type)
        if existing_model:
            await model.save(force_update=True)
        else:
            await model.save()

    async def get_by_key(self, key: str) -> EventType | None:
        model = await EventTypeModel.get_or_none(key=key)
        if model is None:
            return None
        return model.to_domain()

    async def list_all(self) -> list[EventType]:
        models = await EventTypeModel.all()
        return [model.to_domain() for model in models]
