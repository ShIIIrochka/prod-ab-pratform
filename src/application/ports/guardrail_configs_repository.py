from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.value_objects.guardrail_config import GuardrailConfig


class GuardrailConfigsRepositoryPort(ABC):
    @abstractmethod
    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailConfig]:
        """Получить все guardrail-правила эксперимента."""
        raise NotImplementedError

    @abstractmethod
    async def replace_for_experiment(
        self, experiment_id: UUID, configs: list[GuardrailConfig]
    ) -> None:
        """Заменить все guardrail-правила эксперимента (удалить старые, сохранить новые)."""
        raise NotImplementedError

    @abstractmethod
    async def get_for_running_experiments(
        self,
    ) -> dict[UUID, list[GuardrailConfig]]:
        """Один запрос: все конфиги для экспериментов со статусом RUNNING."""
        raise NotImplementedError
