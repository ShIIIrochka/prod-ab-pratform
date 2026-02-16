from __future__ import annotations

from src.application.dto.decide import (
    DecideRequest,
)
from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.domain.aggregates.decision import Decision
from src.domain.exceptions import UserNotFoundError
from src.domain.exceptions.decision import FeatureFlagNotFoundError
from src.domain.services.decision_engine import compute_decision
from src.domain.services.decision_id_generator import (
    generate_deterministic_decision_id,
)


class DecideUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        experiments_repository: ExperimentsRepositoryPort,
        decisions_repository: DecisionsRepositoryPort,
        user_repository: UsersRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository
        self._experiments_repository = experiments_repository
        self._decisions_repository = decisions_repository
        self._user_repository = user_repository
        self._uow = uow

    async def execute(self, data: DecideRequest) -> Decision:
        flag = await self._feature_flags_repository.get_by_key(data.flag_key)

        if flag is None:
            raise FeatureFlagNotFoundError

        user = await self._user_repository.get_by_id(data.subject_id)
        if not user:
            raise UserNotFoundError

        experiment = await self._experiments_repository.get_active_by_flag_key(
            data.flag_key
        )

        decision_result = compute_decision(
            experiment=experiment,
            subject_id=str(data.subject_id),
            attributes=data.attributes,
        )

        if decision_result.applied and experiment:
            value = decision_result.value
            experiment_id = experiment.id
            variant_id = decision_result.variant_id
            variant_name = decision_result.variant_name
            experiment_version = experiment.version
        else:
            value = flag.default_value
            experiment_id = None
            variant_id = None
            variant_name = None
            experiment_version = None

        decision_id = generate_deterministic_decision_id(
            subject_id=data.subject_id,
            flag_key=data.flag_key,
            experiment_id=experiment_id,
            variant_id=str(variant_name),
        )

        existing_decision = await self._decisions_repository.get_by_id(
            decision_id
        )

        if existing_decision:
            decision = existing_decision
        else:
            decision = Decision(
                id=decision_id,
                subject_id=data.subject_id,
                flag_key=data.flag_key,
                value=value,
                experiment_id=experiment_id,
                variant_id=variant_id,
                variant_name=variant_name,
                experiment_version=experiment_version,
            )
            async with self._uow:
                await self._decisions_repository.save(decision)

        return decision
