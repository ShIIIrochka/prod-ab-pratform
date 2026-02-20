from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from src.application.ports.events_repository import EventsRepositoryPort
from src.domain.aggregates.event import AttributionStatus, Event
from src.infra.adapters.db.models.decision import DecisionModel
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
        # Получаем decision_ids для этого эксперимента
        decision_ids = await DecisionModel.filter(
            experiment_id=str(experiment_id)
        ).values_list("id", flat=True)

        if not decision_ids:
            return []

        query = EventModel.filter(
            decision_id__in=[str(d) for d in decision_ids],
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
        grouped = await self.get_by_experiment_grouped_by_variant(
            experiment_id=experiment_id,
            from_time=from_time,
            to_time=to_time,
            attribution_status=attribution_status,
        )
        return grouped.get(variant_name, [])

    async def get_by_experiment_grouped_by_variant(
        self,
        experiment_id: UUID,
        from_time: datetime,
        to_time: datetime,
        attribution_status: AttributionStatus | None = None,
    ) -> dict[str, list[Event]]:
        event_query = EventModel.filter(
            timestamp__gte=from_time,
            timestamp__lt=to_time,
        )
        if attribution_status is not None:
            event_query = event_query.filter(
                attribution_status=attribution_status.value
            )
        candidate_decision_ids = await event_query.distinct().values_list(
            "decision_id", flat=True
        )
        if not candidate_decision_ids:
            return {}

        decisions = await DecisionModel.filter(
            id__in=candidate_decision_ids,
            experiment_id=str(experiment_id),
        ).prefetch_related("variant")

        decision_to_variant: dict[str, str] = {}
        for decision in decisions:
            if decision.variant_id is not None:  # type: ignore
                variant = await decision.variant  # type: ignore
                decision_to_variant[str(decision.id)] = variant.name

        if not decision_to_variant:
            return {}

        event_query = EventModel.filter(
            decision_id__in=list(decision_to_variant.keys()),
            timestamp__gte=from_time,
            timestamp__lt=to_time,
        )
        if attribution_status is not None:
            event_query = event_query.filter(
                attribution_status=attribution_status.value
            )
        event_models = await event_query.all()

        grouped: dict[str, list[Event]] = defaultdict(list)
        for model in event_models:
            variant_name = decision_to_variant.get(model.decision_id)
            if variant_name:
                grouped[variant_name].append(model.to_domain())

        return dict(grouped)
