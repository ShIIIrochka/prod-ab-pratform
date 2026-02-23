from uuid import UUID

from fastapi import APIRouter, HTTPException, Security, status

from src.application.ports.experiment_versions_repository import (
    ExperimentVersionsRepositoryPort,
)
from src.domain.value_objects.experiment_version import ExperimentVersion
from src.presentation.rest.dependencies import Container
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/experiments",
    tags=["Experiment Versions"],
    dependencies=[Security(JWTBackend.auth_required)],
)


def _serialize(v: ExperimentVersion) -> dict:
    return {
        "version": v.version,
        "changed_at": v.changed_at.isoformat(),
        "changed_by": v.changed_by,
        "snapshot": v.snapshot,
    }


@router.get("/{experiment_id}/versions")
async def list_experiment_versions(
    experiment_id: UUID,
    container: Container,
) -> list[dict]:
    repo = container.resolve(ExperimentVersionsRepositoryPort)
    versions = await repo.list_versions(experiment_id)
    return [_serialize(v) for v in versions]


@router.get("/{experiment_id}/versions/{version}")
async def get_experiment_version(
    experiment_id: UUID,
    version: int,
    container: Container,
) -> dict:
    repo = container.resolve(ExperimentVersionsRepositoryPort)
    result = await repo.get_version(experiment_id, version)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for experiment {experiment_id}",
        )
    return _serialize(result)
