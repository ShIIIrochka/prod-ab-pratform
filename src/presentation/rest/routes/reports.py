from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Security

from src.application.dto.reports import ExperimentReportResponse
from src.application.usecases.reports.get_experiment_report import (
    GetExperimentReportUseCase,
)
from src.presentation.rest.dependencies import Container
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/experiments",
    tags=["Reports"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.get("/{experiment_id}/report", response_model=ExperimentReportResponse)
async def get_experiment_report(
    experiment_id: UUID,
    container: Container,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> ExperimentReportResponse:
    now = datetime.now(UTC)
    if from_time is None:
        from_time = now - timedelta(days=90)
    if to_time is None:
        to_time = now

    use_case = container.resolve(GetExperimentReportUseCase)
    return await use_case.execute(
        experiment_id=experiment_id,
        from_time=from_time,
        to_time=to_time,
    )
