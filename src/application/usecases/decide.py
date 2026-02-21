from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from src.application.dto.decide import DecideRequest
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

    async def execute(self, data: DecideRequest) -> dict[str, Decision]:
        user = await self._user_repository.get_by_id(data.subject_id)
        if not user:
            raise UserNotFoundError

        flags_map = await self._feature_flags_repository.get_by_keys(
            data.flag_keys
        )
        missing = [k for k in data.flag_keys if k not in flags_map]
        if missing:
            raise FeatureFlagNotFoundError

        experiments_map = (
            await self._experiments_repository.get_active_by_flag_keys(
                data.flag_keys
            )
        )

        since = datetime.utcnow() - timedelta(days=self._cooldown_period_days)
        active_decisions = (
            await self._decisions_repository.get_active_experiments_by_subject(
                data.subject_id
            )
        )
        recent_decisions = (
            await self._decisions_repository.get_recent_by_subject(
                data.subject_id, since
            )
        )

        active_exp_ids: list[UUID] = [
            d.experiment_id
            for d in active_decisions
            if d.experiment_id is not None
        ]
        active_experiments_by_id = (
            await self._experiments_repository.get_by_ids(active_exp_ids)
        )
        active_experiments = list(active_experiments_by_id.values())

        results: dict[str, DecisionResult] = {}
        for flag_key in data.flag_keys:
            experiment = experiments_map.get(flag_key)
            decision_result = compute_decision(
                experiment=experiment,
                subject_id=str(data.subject_id),
                attributes=data.attributes,
                rotation_period_days=self._rotation_period_days,
            )

            if decision_result.applied and experiment:
                allowed, _ = check_participation_allowed(
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

            results[flag_key] = decision_result

        decisions: dict[str, Decision] = {}
        new_decisions: list[Decision] = []
        decision_ids: list[UUID] = []

        for flag_key in data.flag_keys:
            decision_result = results[flag_key]
            flag = flags_map[flag_key]
            experiment = experiments_map.get(flag_key)

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
                flag_key=flag_key,
                experiment_id=experiment_id,
                variant_id=str(variant_name),
            )
            decision_ids.append(decision_id)
            decisions[flag_key] = Decision(
                id=decision_id,
                subject_id=data.subject_id,
                flag_key=flag_key,
                value=value,
                experiment_id=experiment_id,
                variant_id=variant_id,
                variant_name=variant_name,
                experiment_version=experiment_version,
            )

        existing_decisions = await self._decisions_repository.get_by_ids(
            decision_ids
        )
        for flag_key, decision in decisions.items():
            if decision.id in existing_decisions:
                decisions[flag_key] = existing_decisions[decision.id]
            else:
                new_decisions.append(decision)

        if new_decisions:
            async with self._uow:
                await self._decisions_repository.save_many(new_decisions)

        return decisions
