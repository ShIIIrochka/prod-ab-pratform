from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.value_objects.guardrail_trigger import GuardrailTrigger


class GuardrailTriggersRepositoryPort(ABC):
    @abstractmethod
    async def save(self, trigger: GuardrailTrigger) -> None:
        """Сохранить запись о срабатывании guardrail."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailTrigger]:
        """Получить историю срабатываний для эксперимента."""
        raise NotImplementedError
