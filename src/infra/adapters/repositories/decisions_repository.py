from __future__ import annotations

from uuid import UUID

from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.domain.aggregates.decision import Decision
from src.infra.adapters.db.models.decision import DecisionModel


class DecisionsRepository(DecisionsRepositoryPort):
    async def save(self, decision: Decision) -> None:
        model = DecisionModel.from_domain(decision)
        await model.save()

    async def get_by_id(self, decision_id: UUID) -> Decision | None:
        model = await DecisionModel.get_or_none(id=decision_id)
        if model is None:
            return None
        return model.to_domain()
