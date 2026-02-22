from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.guardrail_config import GuardrailConfig
from src.infra.adapters.db.models.experiment import ExperimentModel
from src.infra.adapters.db.models.guardrail_config import GuardrailConfigModel


class GuardrailConfigsRepository(GuardrailConfigsRepositoryPort):
    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailConfig]:
        models = await GuardrailConfigModel.filter(
            experiment_id=experiment_id
        ).all()
        return [m.to_domain() for m in models]

    async def get_by_experiment_ids(
        self, experiment_ids: list[UUID]
    ) -> dict[UUID, list[GuardrailConfig]]:
        if not experiment_ids:
            return {}
        models = await GuardrailConfigModel.filter(
            experiment_id__in=experiment_ids
        ).all()
        result: dict[UUID, list[GuardrailConfig]] = defaultdict(list)
        for model in models:
            exp_id: UUID = model.experiment_id  # type: ignore[assignment]
            result[exp_id].append(model.to_domain())
        return dict(result)

    async def replace_for_experiment(
        self, experiment_id: UUID, configs: list[GuardrailConfig]
    ) -> None:
        await GuardrailConfigModel.filter(experiment_id=experiment_id).delete()
        if configs:
            new_models = [
                GuardrailConfigModel.from_domain(config, experiment_id)
                for config in configs
            ]
            await GuardrailConfigModel.bulk_create(new_models)

    async def get_for_running_experiments(
        self,
    ) -> dict[UUID, list[GuardrailConfig]]:
        """Один запрос: все конфиги для экспериментов со статусом RUNNING."""
        running_ids = await ExperimentModel.filter(
            status=ExperimentStatus.RUNNING
        ).values_list("id", flat=True)

        if not running_ids:
            return {}

        models = await GuardrailConfigModel.filter(
            experiment_id__in=running_ids
        ).all()

        result: dict[UUID, list[GuardrailConfig]] = defaultdict(list)
        for model in models:
            exp_id: UUID = model.experiment_id  # type: ignore[assignment]
            result[exp_id].append(model.to_domain())

        return dict(result)
