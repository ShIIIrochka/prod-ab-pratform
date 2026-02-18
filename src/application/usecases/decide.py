from __future__ import annotations

from datetime import datetime, timedelta

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
from src.domain.services.decision_engine import DecisionResult, compute_decision
from src.domain.services.decision_id_generator import (
    generate_deterministic_decision_id,
)
from src.domain.services.participation_guard import (
    check_participation_allowed,
)


class DecideUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        experiments_repository: ExperimentsRepositoryPort,
        decisions_repository: DecisionsRepositoryPort,
        user_repository: UsersRepositoryPort,
        uow: UnitOfWorkPort,
        max_concurrent_experiments: int,
        cooldown_period_days: int,
        experiments_before_cooldown: int,
        cooldown_experiment_probability: float,
        rotation_period_days: int,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository
        self._experiments_repository = experiments_repository
        self._decisions_repository = decisions_repository
        self._user_repository = user_repository
        self._uow = uow
        self._max_concurrent_experiments = max_concurrent_experiments
        self._cooldown_period_days = cooldown_period_days
        self._experiments_before_cooldown = experiments_before_cooldown
        self._cooldown_experiment_probability = cooldown_experiment_probability
        self._rotation_period_days = rotation_period_days

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
            rotation_period_days=self._rotation_period_days,
        )

        if decision_result.applied and experiment:
            active_decisions = await self._decisions_repository.get_active_experiments_by_subject(
                data.subject_id
            )
            active_experiments = []
            for decision in active_decisions:
                if decision.experiment_id:
                    exp = await self._experiments_repository.get_by_id(
                        decision.experiment_id
                    )
                    if exp:
                        active_experiments.append(exp)

            since = datetime.utcnow() - timedelta(
                days=self._cooldown_period_days
            )
            recent_decisions = (
                await self._decisions_repository.get_recent_by_subject(
                    data.subject_id, since
                )
            )

            allowed, reason = check_participation_allowed(
                subject_id=str(data.subject_id),
                experiment=experiment,
                active_experiments=active_experiments,
                recent_decisions=recent_decisions,
                current_time=datetime.utcnow(),
                max_concurrent_experiments=self._max_concurrent_experiments,
                cooldown_period_days=self._cooldown_period_days,
                experiments_before_cooldown=self._experiments_before_cooldown,
                cooldown_experiment_probability=self._cooldown_experiment_probability,
            )

            if not allowed:
                decision_result = DecisionResult(
                    applied=False,
                    value="",
                    variant_id=None,
                    variant_name=None,
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
