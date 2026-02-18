from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.domain.aggregates.decision import Decision
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.infra.adapters.db.models.decision import DecisionModel


class DecisionsRepository(DecisionsRepositoryPort):
    async def save(self, decision: Decision) -> None:
        existing_model = await DecisionModel.get_or_none(id=decision.id)
        model = DecisionModel.from_domain(decision)
        if existing_model:
            await model.save(force_update=True)
        else:
            await model.save()

    async def get_by_id(self, decision_id: UUID) -> Decision | None:
        model = await DecisionModel.get_or_none(id=decision_id)
        if model is None:
            return None
        return await model.to_domain()

    async def get_active_experiments_by_subject(
        self, subject_id: str
    ) -> list[Decision]:
        models = await DecisionModel.filter(
            user_id=subject_id,
            experiment_id__isnull=False,  # Исправлено: было experiment__isnull=False
            experiment__status__in=[
                ExperimentStatus.RUNNING.value,
                ExperimentStatus.PAUSED.value,
            ],
        ).prefetch_related("experiment", "variant")
        return [await model.to_domain() for model in models]

    async def get_recent_by_subject(
        self,
        subject_id: str,
        since: datetime,
    ) -> list[Decision]:
        models = (
            await DecisionModel.filter(user_id=subject_id, timestamp__gte=since)
            .order_by("-timestamp")
            .prefetch_related("experiment", "variant")
        )
        return [await model.to_domain() for model in models]
