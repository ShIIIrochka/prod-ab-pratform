from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.ports.events_repository import EventsRepositoryPort
from src.domain.aggregates.event import AttributionStatus, Event
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
        models = await EventModel.filter(
            decision_id=decision_id,
            event_type_key="exposure",
        ).all()
        return [model.to_domain() for model in models]

    async def get_by_experiment(
        self,
        experiment_id: UUID,
        from_time: datetime,
        to_time: datetime,
        attribution_status: AttributionStatus | None = None,
    ) -> list[Event]:
        query = EventModel.filter(
            decision__experiment_id=str(experiment_id),
            timestamp__gte=from_time,
            timestamp__lt=to_time,
        )
        if attribution_status is not None:
            query = query.filter(attribution_status=attribution_status.value)
        models = await query.all()
        return [m.to_domain() for m in models]

    async def get_by_experiment_and_variant(
        self,
        experiment_id: UUID,
        variant_name: str,
        from_time: datetime,
        to_time: datetime,
        attribution_status: AttributionStatus | None = None,
    ) -> list[Event]:
        query = EventModel.filter(
            decision__experiment_id=str(experiment_id),
            decision__variant__name=variant_name,
            timestamp__gte=from_time,
            timestamp__lt=to_time,
        )
        if attribution_status is not None:
            query = query.filter(attribution_status=attribution_status.value)
        models = await query.all()
        return [m.to_domain() for m in models]
