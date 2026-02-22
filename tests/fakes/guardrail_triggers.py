"""Fake GuardrailTriggersRepository — in-memory storage inheriting from port."""

from __future__ import annotations

from uuid import UUID

from src.application.ports.guardrail_triggers_repository import (
    GuardrailTriggersRepositoryPort,
)
from src.domain.value_objects.guardrail_trigger import GuardrailTrigger


class FakeGuardrailTriggersRepository(GuardrailTriggersRepositoryPort):
    """In-memory guardrail triggers for unit tests."""

    def __init__(self) -> None:
        self._triggers: list[GuardrailTrigger] = []

    async def save(self, trigger: GuardrailTrigger) -> None:
        self._triggers.append(trigger)

    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailTrigger]:
        return [t for t in self._triggers if t.experiment_id == experiment_id]

    def saved_triggers(self) -> list[GuardrailTrigger]:
        """Helper for assertions."""
        return list(self._triggers)
