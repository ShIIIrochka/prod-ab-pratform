from __future__ import annotations

from uuid import UUID

from application.ports.experiments_repository import ExperimentsRepositoryPort
from domain.aggregates.experiment import Experiment
from domain.entities.variant import Variant
from domain.value_objects.experiment_status import ExperimentStatus
from domain.value_objects.targeting_rule import TargetingRule
from infra.adapters.db.models.experiment import ExperimentModel
from infra.adapters.db.models.variant import VariantModel


class ExperimentsRepository(ExperimentsRepositoryPort):
    async def get_active_by_flag_key(
        self, flag_key: str
    ) -> Experiment | None:
        # Получаем эксперимент со статусом RUNNING
        model = await ExperimentModel.get_or_none(
            flag_key=flag_key,
            status=ExperimentStatus.RUNNING.value,
        ).prefetch_related("variants")

        if model is None:
            return None

        # Загружаем варианты
        variants = []
        variant_models = await VariantModel.filter(experiment_id=model.id).all()
        for variant_model in variant_models:
            variants.append(
                Variant(
                    id=UUID(variant_model.id),
                    name=variant_model.name,
                    value=variant_model.value,
                    weight=variant_model.weight,
                    is_control=variant_model.is_control,
                )
            )

        # Парсим targeting rule
        targeting_rule = None
        if model.targeting_rule_json:
            targeting_rule = TargetingRule.from_dict(model.targeting_rule_json)

        return Experiment(
            id=UUID(model.id),
            name=model.name,
            flag_key=model.flag_key,
            status=ExperimentStatus(model.status),
            version=model.version,
            audience_fraction=model.audience_fraction,
            variants=variants,
            targeting_rule=targeting_rule,
            primary_metric_key=model.primary_metric_key,
        )

    async def get_active_by_flag_key_async(
        self, flag_key: str
    ) -> Experiment | None:
        """Асинхронное получение активного эксперимента."""
        return await self._get_active_by_flag_key_async(flag_key)
