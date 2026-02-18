from __future__ import annotations

from uuid import UUID

from src.application.ports.events_repository import EventsRepositoryPort
from src.domain.aggregates.event import Event
from src.infra.adapters.db.models.event import EventModel


class EventsRepository(EventsRepositoryPort):
    async def save(self, event: Event) -> None:
        existing_model = await EventModel.get_or_none(id=event.id)
        model = EventModel.from_domain(event)
        if existing_model:
            await model.save(force_update=True)
        else:
            await model.save()

    async def get_by_id(self, event_id: UUID) -> Event | None:
        model = await EventModel.get_or_none(id=event_id)
        if model is None:
            return None
        return model.to_domain()

    async def exists(self, event_id: UUID) -> bool:
        return await EventModel.exists(id=event_id)

    async def get_by_decision_id(
        self, decision_id: str, event_type_key: str | None = None
    ) -> list[Event]:
        query = EventModel.filter(decision_id=decision_id)
        if event_type_key:
            query = query.filter(event_type_key=event_type_key)
        models = await query.all()
        return [model.to_domain() for model in models]

    async def get_exposure_by_decision_id(
        self, decision_id: str
    ) -> list[Event]:
        """Получить только exposure-события по decision_id."""
        models = await EventModel.filter(
            decision_id=decision_id,
            event_type_key="exposure",
        ).all()
        return [model.to_domain() for model in models]
