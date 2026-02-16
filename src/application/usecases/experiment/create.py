from __future__ import annotations

from src.application.dto.experiment import ExperimentCreateRequest
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.exceptions.decision import (
    FeatureFlagNotFoundError,
    VariantNameAlreadyExistsError,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule


class CreateExperimentUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._feature_flags_repository = feature_flags_repository
        self._uow = uow

    async def execute(
        self, data: ExperimentCreateRequest, owner_id: str
    ) -> Experiment:
        flag = await self._feature_flags_repository.get_by_key(data.flag_key)
        if not flag:
            raise FeatureFlagNotFoundError

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
            completion=None,
        )
        try:
            async with self._uow:
                await self._experiments_repository.save(experiment)
        except ValueError as e:
            if "Variant name already exists" in str(e):
                raise VariantNameAlreadyExistsError from e
            raise
        return experiment
