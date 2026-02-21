from __future__ import annotations

from uuid import UUID, uuid4

from src.application.dto.experiment import ExperimentUpdateRequest
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.exceptions.decision import (
    ExperimentNotFoundError,
    FeatureFlagNotFoundError,
    VariantNameAlreadyExistsError,
    VariantValueTypeError,
)
from src.domain.value_objects.guardrail_config import GuardrailConfig
from src.domain.value_objects.targeting_rule import TargetingRule


class UpdateExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        guardrail_configs_repository: GuardrailConfigsRepositoryPort,
        metrics_repository: MetricsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._feature_flags_repository = feature_flags_repository
        self._guardrail_configs_repository = guardrail_configs_repository
        self._metrics_repository = metrics_repository
        self._uow = uow

    async def execute(
        self, experiment_id: UUID, data: ExperimentUpdateRequest
    ) -> Experiment:
        experiment = await self._experiments_repository.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        if not experiment.can_be_edited():
            msg = f"Cannot edit experiment in status {experiment.status}"
            raise ValueError(msg)

        if data.name is not None:
            experiment.name = data.name

        if data.audience_fraction is not None:
            experiment.audience_fraction = data.audience_fraction

        if data.variants is not None:
            flag = await self._feature_flags_repository.get_by_key(
                experiment.flag_key
            )
            if not flag:
                raise FeatureFlagNotFoundError
            for v in data.variants:
                try:
                    flag.validate_variant_value(v.value)
                except ValueError as exc:
                    raise VariantValueTypeError(message=str(exc)) from exc
            experiment.variants = [
                Variant(
                    id=uuid4(),
                    name=v.name,
                    value=v.value,
                    weight=v.weight,
                    is_control=v.is_control,
                )
                for v in data.variants
            ]

        if data.targeting_rule is not None:
            experiment.targeting_rule = TargetingRule(
                rule_expression=data.targeting_rule
            )

        if data.target_metric_key is not None:
            m = await self._metrics_repository.get_by_key(
                data.target_metric_key
            )
            if not m:
                msg = f"Metric '{data.target_metric_key}' not found"
                raise ValueError(msg)
            experiment.target_metric_key = data.target_metric_key

        if data.metric_keys is not None:
            metric_keys: list[str] = []
            for mk in data.metric_keys:
                m = await self._metrics_repository.get_by_key(mk)
                if not m:
                    msg = f"Metric '{mk}' not found"
                    raise ValueError(msg)
                metric_keys.append(mk)
            experiment.metric_keys = metric_keys

        new_guardrails: list[GuardrailConfig] | None = None
        if data.guardrails is not None:
            new_guardrails = []
            for g in data.guardrails:
                m = await self._metrics_repository.get_by_key(g.metric_key)
                if not m:
                    msg = f"Guardrail metric '{g.metric_key}' not found"
                    raise ValueError(msg)
                new_guardrails.append(
                    GuardrailConfig(
                        metric_key=g.metric_key,
                        threshold=g.threshold,
                        observation_window_minutes=g.observation_window_minutes,
                        action=g.action,
                    )
                )

        try:
            async with self._uow:
                await self._experiments_repository.save(experiment)
                if new_guardrails is not None:
                    await self._guardrail_configs_repository.replace_for_experiment(
                        experiment_id, new_guardrails
                    )
        except ValueError as e:
            if "Variant name already exists" in str(e):
                raise VariantNameAlreadyExistsError from e
            raise
        return experiment
