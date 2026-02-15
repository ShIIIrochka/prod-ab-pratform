from __future__ import annotations

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.infra.adapters.db.models.experiment import ExperimentModel


class ExperimentsRepository(ExperimentsRepositoryPort):
    async def get_active_by_flag_key(self, flag_key: str) -> Experiment | None:
        model = (
            await ExperimentModel.get_or_none(
                flag_key=flag_key,
                status=ExperimentStatus.RUNNING.value,
            )
            .prefetch_related("variants")
            .prefetch_related("owner")
        )

        if model is None:
            return None
        return model.to_domain()
