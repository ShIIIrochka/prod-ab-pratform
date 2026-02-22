"""Fake ExperimentsRepository — in-memory storage inheriting from port."""

from __future__ import annotations

from uuid import UUID

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_status import ExperimentStatus


class FakeExperimentsRepository(ExperimentsRepositoryPort):
    """In-memory experiments store for unit tests."""

    def __init__(self) -> None:
        self._store: dict[UUID, Experiment] = {}

    async def get_by_id(self, experiment_id: UUID) -> Experiment | None:
        return self._store.get(experiment_id)

    async def get_by_ids(self, ids: list[UUID]) -> dict[UUID, Experiment]:
        return {eid: self._store[eid] for eid in ids if eid in self._store}

    async def save(self, experiment: Experiment) -> None:
        self._store[experiment.id] = experiment

    async def get_active_by_flag_key(self, flag_key: str) -> Experiment | None:
        for e in self._store.values():
            if e.flag_key == flag_key and e.status.is_active():
                return e
        return None

    async def get_active_by_flag_keys(
        self, keys: list[str]
    ) -> dict[str, Experiment]:
        result: dict[str, Experiment] = {}
        for e in self._store.values():
            if e.flag_key in keys and e.status.is_active():
                result[e.flag_key] = e
        return result

    async def list_all(
        self,
        flag_key: str | None = None,
        status: ExperimentStatus | None = None,
    ) -> list[Experiment]:
        results = list(self._store.values())
        if flag_key:
            results = [e for e in results if e.flag_key == flag_key]
        if status:
            results = [e for e in results if e.status == status]
        return results
