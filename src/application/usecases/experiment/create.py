from __future__ import annotations

from src.application.dto.experiment import ExperimentCreateRequest
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.uow import UnitOfWorkPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.guardrail_config import GuardrailConfig
from src.domain.entities.variant import Variant
from src.domain.exceptions import UserNotFoundError
from src.domain.exceptions.decision import (
    FeatureFlagNotFoundError,
    VariantNameAlreadyExistsError,
    VariantValueTypeError,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule


class CreateExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        user_repository: UsersRepositoryPort,
        metrics_repository: MetricsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._feature_flags_repository = feature_flags_repository
        self._user_repository = user_repository
        self._metrics_repository = metrics_repository
        self._uow = uow

    async def execute(
        self, data: ExperimentCreateRequest, owner_id: str
    ) -> Experiment:
        flag = await self._feature_flags_repository.get_by_key(data.flag_key)
        if not flag:
            raise FeatureFlagNotFoundError

        user = await self._user_repository.get_by_id(owner_id)
        if not user:
            raise UserNotFoundError

        active_experiments = await self._experiments_repository.list_all(
            flag_key=data.flag_key
        )
        for exp in active_experiments:
            if exp.status in (
                ExperimentStatus.RUNNING,
                ExperimentStatus.PAUSED,
            ):
                msg = (
                    f"Active experiment already exists for flag {data.flag_key}"
                )
                raise ValueError(msg)

        for v in data.variants:
            try:
                flag.validate_variant_value(v.value)
            except ValueError as exc:
                raise VariantValueTypeError(message=str(exc)) from exc

        variants = [
            Variant(
                name=v.name,
                value=v.value,
                weight=v.weight,
                is_control=v.is_control,
            )
            for v in data.variants
        ]

        targeting_rule = None
        if data.targeting_rule:
            targeting_rule = TargetingRule(rule_expression=data.targeting_rule)

        if data.target_metric_key:
            m = await self._metrics_repository.get_by_key(
                data.target_metric_key
            )
            if not m:
                msg = f"Metric '{data.target_metric_key}' not found"
                raise ValueError(msg)

        metric_keys: list[str] = []
        for mk in data.metric_keys or []:
            m = await self._metrics_repository.get_by_key(mk)
            if not m:
                msg = f"Metric '{mk}' not found"
                raise ValueError(msg)
            metric_keys.append(mk)

        guardrail_configs: list[GuardrailConfig] = []
        for g in data.guardrails or []:
            m = await self._metrics_repository.get_by_key(g.metric_key)
            if not m:
                msg = f"Guardrail metric '{g.metric_key}' not found"
                raise ValueError(msg)
            guardrail_configs.append(
                GuardrailConfig(
                    metric_key=g.metric_key,
                    threshold=g.threshold,
                    observation_window_minutes=g.observation_window_minutes,
                    action=g.action,
                )
            )

        experiment = Experiment(
            flag_key=data.flag_key,
            name=data.name,
            status=ExperimentStatus.DRAFT,
            version=1,
            audience_fraction=data.audience_fraction,
            variants=variants,
            targeting_rule=targeting_rule,
            owner_id=owner_id,
            approvals=[],
            guardrails=guardrail_configs,
            completion=None,
            target_metric_key=data.target_metric_key,
            metric_keys=metric_keys,
        )
        try:
            async with self._uow:
                await self._experiments_repository.save(experiment)
        except ValueError:
            raise VariantNameAlreadyExistsError
        return experiment
