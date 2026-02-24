from uuid import UUID

from src.application.dto.experiment import CompleteExperimentRequest
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.application.ports.uow import UnitOfWorkPort
from src.application.services.domain_event_publisher import DomainEventPublisher
from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.learning import Learning
from src.domain.exceptions.decision import ExperimentNotFoundError


class CompleteExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        uow: UnitOfWorkPort,
        notification_dispatcher: DomainEventPublisher,
        learnings_repository: LearningsRepositoryPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._uow = uow
        self._publisher = notification_dispatcher
        self._learnings_repository = learnings_repository

    async def execute(
        self,
        experiment_id: UUID,
        completed_by: str,
        data: CompleteExperimentRequest,
    ) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        experiment.complete(
            outcome=data.outcome,
            comment=data.comment,
            completed_by=completed_by,
            winner_variant_id=data.winner_variant_id,
        )
        async with self._uow:
            await self._experiments_repository.save(experiment)

        await self._publisher.publish_from(experiment)
        learning = Learning.from_completed_experiment(experiment)
        await self._learnings_repository.save(learning)

        return experiment
