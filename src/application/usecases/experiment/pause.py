from __future__ import annotations

from uuid import UUID

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.experiment import Experiment
from src.domain.exceptions.decision import ExperimentNotFoundError


class PauseExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._uow = uow

    async def execute(self, experiment_id: UUID) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        experiment.pause()
        async with self._uow:
            await self._experiments_repository.save(experiment)
        return experiment
