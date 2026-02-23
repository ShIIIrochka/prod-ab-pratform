"""Fake GuardrailConfigsRepository — in-memory storage inheriting from port."""

from __future__ import annotations

from uuid import UUID

from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.domain.entities.guardrail_config import GuardrailConfig


class FakeGuardrailConfigsRepository(GuardrailConfigsRepositoryPort):
    """In-memory guardrail configs for unit tests."""

    def __init__(self) -> None:
        # experiment_id -> list[GuardrailConfig]
        self._by_experiment: dict[UUID, list[GuardrailConfig]] = {}
        self._for_running: dict[UUID, list[GuardrailConfig]] = {}
        self._get_for_running_calls = 0

    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailConfig]:
        return self._by_experiment.get(experiment_id, [])

    async def get_by_experiment_ids(
        self, experiment_ids: list[UUID]
    ) -> dict[UUID, list[GuardrailConfig]]:
        return {
            eid: self._by_experiment[eid]
            for eid in experiment_ids
            if eid in self._by_experiment
        }

    async def replace_for_experiment(
        self, experiment_id: UUID, configs: list[GuardrailConfig]
    ) -> None:
        self._by_experiment[experiment_id] = list(configs)

    async def get_for_running_experiments(
        self,
    ) -> dict[UUID, list[GuardrailConfig]]:
        self._get_for_running_calls += 1
        return dict(self._for_running)

    def set_for_running(
        self, experiment_id: UUID, configs: list[GuardrailConfig]
    ) -> None:
        """Helper to populate get_for_running_experiments for tests."""
        self._for_running[experiment_id] = configs
