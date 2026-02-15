from __future__ import annotations

from uuid import UUID

from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.domain.aggregates.decision import Decision
from src.infra.adapters.db.models.decision import DecisionModel


class DecisionsRepository(DecisionsRepositoryPort):
    async def save(self, decision: Decision) -> None:
        """Сохраняет решение в БД.

        Использует get_or_create для защиты от race conditions при параллельных запросах.
        """
        await DecisionModel.get_or_create(
            id=str(decision.id),
            defaults={
                "subject_id": decision.subject_id,
                "flag_key": decision.flag_key,
                "value": decision.value,
                "experiment_id": str(decision.experiment_id)
                if decision.experiment_id
                else None,
                "variant_id": decision.variant_id,
                "experiment_version": decision.experiment_version,
                "timestamp": decision.timestamp,
            },
        )

    async def get_by_id(self, decision_id: str) -> Decision | None:
        """Получает решение по decision_id."""
        model = await DecisionModel.get_or_none(id=decision_id)
        if model is None:
            return None

        return Decision(
            id=UUID(model.id),
            subject_id=model.subject_id,
            flag_key=model.flag_key,
            value=model.value,
            experiment_id=UUID(model.experiment_id)
            if model.experiment_id
            else None,
            variant_id=model.variant_id,
            experiment_version=model.experiment_version,
            timestamp=model.timestamp,
        )
