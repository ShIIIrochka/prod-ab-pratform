from uuid import UUID

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.application.services.domain_event_publisher import DomainEventPublisher
from src.domain.aggregates.experiment import Experiment
from src.domain.exceptions.decision import ExperimentNotFoundError
from src.domain.exceptions.users import UserNotFoundError


class LaunchExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        users_repository: UsersRepositoryPort,
        uow: UnitOfWorkPort,
        notification_dispatcher: DomainEventPublisher,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._users_repository = users_repository
        self._uow = uow
        self._publisher = notification_dispatcher

    async def execute(
        self, experiment_id: UUID, launching_user_id: str
    ) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        owner = await self._users_repository.get_by_id(experiment.owner_id)
        if not owner:
            raise UserNotFoundError

        launching_user = await self._users_repository.get_by_id(
            launching_user_id
        )
        if not launching_user:
            raise UserNotFoundError

        experiment.launch(owner, launching_user)
        async with self._uow:
            await self._experiments_repository.save(experiment)

        await self._publisher.publish_from(experiment)

        return experiment
