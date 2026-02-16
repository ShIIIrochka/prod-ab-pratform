from __future__ import annotations

from uuid import UUID

from src.application.dto.experiment import RequestChangesRequest
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.domain.aggregates.experiment import Experiment
from src.domain.exceptions.decision import ExperimentNotFoundError
from src.domain.exceptions.users import UserNotFoundError


class RequestChangesUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        users_repository: UsersRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._users_repository = users_repository
        self._uow = uow

    async def execute(
        self,
        experiment_id: UUID,
        requesting_user_id: str,
        data: RequestChangesRequest,
    ) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        owner = await self._users_repository.get_by_id(experiment.owner_id)
        if not owner:
            raise UserNotFoundError

        requesting_user = await self._users_repository.get_by_id(
            requesting_user_id
        )
        if not requesting_user:
            raise UserNotFoundError

        experiment.request_changes(owner, requesting_user, data.comment)
        async with self._uow:
            await self._experiments_repository.save(experiment)
        return experiment
