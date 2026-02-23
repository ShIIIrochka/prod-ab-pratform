from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_status import ExperimentStatus


class ListExperimentsUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
    ) -> None:
        self._experiments_repository = experiments_repository

    async def execute(
        self,
        flag_key: str | None = None,
        status: ExperimentStatus | None = None,
    ) -> list[Experiment]:
        return await self._experiments_repository.list_all(
            flag_key=flag_key, status=status
        )
