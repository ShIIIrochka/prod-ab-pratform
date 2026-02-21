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


# Unix timestamp of 2001-01-01 00:00:00 UTC — avoid treating millis or tiny values as valid
_REPORT_MIN_TIMESTAMP = 978307200


@router.get("/{experiment_id}/report", response_model=ExperimentReportResponse)
async def get_experiment_report(
    experiment_id: UUID,
    container: Container,
    from_time: int | None = None,
    to_time: int | None = None,
) -> ExperimentReportResponse:
    now = datetime.now(UTC)
    if from_time is not None and from_time < _REPORT_MIN_TIMESTAMP:
        from_time = None
    _from = (
        datetime.fromtimestamp(from_time, tz=UTC)
        if from_time is not None
        else now - timedelta(days=90)
    )
    if to_time is not None and to_time < _REPORT_MIN_TIMESTAMP:
        to_time = None
    _to = (
        datetime.fromtimestamp(to_time, tz=UTC) if to_time is not None else now
    )

    use_case = container.resolve(GetExperimentReportUseCase)
    return await use_case.execute(
        experiment_id=experiment_id,
        from_time=_from,
        to_time=_to,
    )
