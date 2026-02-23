from uuid import UUID

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.exceptions.decision import ExperimentNotFoundError


class GetExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
    ) -> None:
        self._experiments_repository = experiments_repository

    async def execute(self, experiment_id: UUID) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError
        return experiment
