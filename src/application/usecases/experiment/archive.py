from uuid import UUID

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.application.services.domain_event_publisher import DomainEventPublisher
from src.domain.aggregates.experiment import Experiment
from src.domain.exceptions.decision import ExperimentNotFoundError


class ArchiveExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        uow: UnitOfWorkPort,
        notification_dispatcher: DomainEventPublisher,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._uow = uow
        self._publisher = notification_dispatcher

    async def execute(self, experiment_id: UUID) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        experiment.archive()
        async with self._uow:
            await self._experiments_repository.save(experiment)

        await self._publisher.publish_from(experiment)

        return experiment
