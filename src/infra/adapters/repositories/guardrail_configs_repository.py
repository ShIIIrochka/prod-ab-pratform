from __future__ import annotations

from uuid import UUID

from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.domain.value_objects.guardrail_config import GuardrailConfig
from src.infra.adapters.db.models.guardrail_config import GuardrailConfigModel


class GuardrailConfigsRepository(GuardrailConfigsRepositoryPort):
    async def get_by_experiment_id(
        self, experiment_id: UUID
    ) -> list[GuardrailConfig]:
        models = await GuardrailConfigModel.filter(
            experiment_id=str(experiment_id)
        ).all()
        return [m.to_domain() for m in models]

    async def replace_for_experiment(
        self, experiment_id: UUID, configs: list[GuardrailConfig]
    ) -> None:
        await GuardrailConfigModel.filter(
            experiment_id=str(experiment_id)
        ).delete()
        if configs:
            new_models = [
                GuardrailConfigModel.from_domain(config, experiment_id)
                for config in configs
            ]
            await GuardrailConfigModel.bulk_create(new_models)
