from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_status import ExperimentStatus


class ExperimentsRepositoryPort(ABC):
    @abstractmethod
    async def get_active_by_flag_key(self, flag_key: str) -> Experiment | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_flag_keys(
        self, keys: list[str]
    ) -> dict[str, Experiment]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, experiment: Experiment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, experiment_id: UUID) -> Experiment | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_ids(self, ids: list[UUID]) -> dict[UUID, Experiment]:
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self,
        flag_key: str | None = None,
        status: ExperimentStatus | None = None,
    ) -> list[Experiment]:
        raise NotImplementedError
