from __future__ import annotations

from uuid import UUID

from src.application.ports.guardrail_triggers_repository import (
    GuardrailTriggersRepositoryPort,
)
from src.domain.value_objects.guardrail_trigger import GuardrailTrigger
from src.infra.adapters.db.models.guardrail_trigger import GuardrailTriggerModel


class GuardrailTriggersRepository(GuardrailTriggersRepositoryPort):
    async def save(self, trigger: GuardrailTrigger) -> None:
        model = GuardrailTriggerModel.from_domain(trigger)
        await model.save()

    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailTrigger]:
        models = (
            await GuardrailTriggerModel.filter(experiment_id=str(experiment_id))
            .order_by("-triggered_at")
            .all()
        )
        return [m.to_domain() for m in models]
