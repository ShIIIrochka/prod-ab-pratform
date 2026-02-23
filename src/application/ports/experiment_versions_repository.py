from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_version import ExperimentVersion


class ExperimentVersionsRepositoryPort(ABC):
    @abstractmethod
    async def save_snapshot(
        self,
        experiment_id: UUID,
        version: int,
        snapshot: Experiment,
        changed_by: str | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_versions(
        self, experiment_id: UUID
    ) -> list[ExperimentVersion]:
        raise NotImplementedError

    @abstractmethod
    async def get_version(
        self, experiment_id: UUID, version: int
    ) -> ExperimentVersion | None:
        raise NotImplementedError
