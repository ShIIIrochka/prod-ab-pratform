from __future__ import annotations

from uuid import UUID

from src.application.ports.experiment_versions_repository import (
    ExperimentVersionsRepositoryPort,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_version import (
    ExperimentVersion,
    experiment_to_snapshot,
)
from src.infra.adapters.db.models.experiment_version import (
    ExperimentVersionModel,
)


def _to_domain(model: ExperimentVersionModel) -> ExperimentVersion:
    return model.to_domain()


class ExperimentVersionsRepository(ExperimentVersionsRepositoryPort):
    async def save_snapshot(
        self,
        experiment_id: UUID,
        version: int,
        snapshot: Experiment,
        changed_by: str | None = None,
    ) -> None:
        existing = await ExperimentVersionModel.get_or_none(
            experiment_id=experiment_id, version=version
        )
        if existing:
            return
        await ExperimentVersionModel.create(
            experiment_id=experiment_id,
            version=version,
            snapshot=experiment_to_snapshot(snapshot),
            changed_by=changed_by,
        )

    async def list_versions(
        self, experiment_id: UUID
    ) -> list[ExperimentVersion]:
        models = (
            await ExperimentVersionModel.filter(experiment_id=experiment_id)
            .order_by("version")
            .all()
        )
        return [_to_domain(m) for m in models]

    async def get_version(
        self, experiment_id: UUID, version: int
    ) -> ExperimentVersion | None:
        model = await ExperimentVersionModel.get_or_none(
            experiment_id=experiment_id, version=version
        )
        return _to_domain(model) if model else None
