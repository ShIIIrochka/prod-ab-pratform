from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Security

from src.application.dto.experiment import (
    ExperimentListResponse,
    ExperimentResponse,
)
from src.application.dto.learnings import GetSimilarCriteria
from src.application.usecases import GetSimilarExperimentsUseCase
from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_completion import ExperimentOutcome
from src.presentation.rest.dependencies import Container
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/learnings",
    tags=["Learnings"],
    dependencies=[Security(JWTBackend.auth_required)],
)


def _to_response(experiment: Experiment) -> ExperimentResponse:
    return ExperimentResponse.model_validate(experiment)


@router.get("/similar", response_model=ExperimentListResponse)
async def get_similar_experiments(
    container: Container,
    q: str | None = Query(None, description="Full-text search query"),
    flag_key: str | None = Query(
        None, description="Filter by feature flag key"
    ),
    owner_id: str | None = Query(
        None, description="Filter by experiment owner"
    ),
    outcome: ExperimentOutcome | None = Query(
        None, description="Filter by completion outcome"
    ),
    date_from: str | None = Query(
        None, description="Filter by completed_at >= (ISO datetime)"
    ),
    date_to: str | None = Query(
        None, description="Filter by completed_at <= (ISO datetime)"
    ),
    target_metric_key: str | None = Query(
        None, description="Filter by primary metric key"
    ),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> ExperimentListResponse:
    date_from_dt: datetime | None = None
    date_to_dt: datetime | None = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(
                date_from.replace("Z", "+00:00")
            )
        except ValueError:
            pass
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            pass
    criteria = GetSimilarCriteria(
        query=q,
        flag_key=flag_key,
        owner_id=owner_id,
        outcome=outcome,
        date_from=date_from_dt,
        date_to=date_to_dt,
        target_metric_key=target_metric_key,
        limit=limit,
    )
    use_case = container.resolve(GetSimilarExperimentsUseCase)
    experiments = await use_case.execute(criteria)
    return ExperimentListResponse(
        experiments=[_to_response(e) for e in experiments]
    )
