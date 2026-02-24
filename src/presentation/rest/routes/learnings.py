from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security

from src.application.dto.learnings import (
    GetSimilarCriteria,
    LearningResponse,
    SimilarExperimentsListResponse,
    UpdateLearningRequest,
)
from src.application.dto.user import UserResponse
from src.application.usecases import (
    GetSimilarExperimentsUseCase,
    UpdateExperimentLearningUseCase,
)
from src.domain.exceptions.learnings import LearningNotFoundError
from src.domain.value_objects.experiment_completion import ExperimentOutcome
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import Container, require_roles
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/learnings",
    tags=["Learnings"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.get("/similar", response_model=SimilarExperimentsListResponse)
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
) -> SimilarExperimentsListResponse:
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
    learnings = await use_case.execute(criteria)
    return SimilarExperimentsListResponse(
        learnings=[LearningResponse.model_validate(ler) for ler in learnings]
    )


@router.patch(
    "/experiments/{experiment_id}",
    response_model=LearningResponse,
)
async def update_experiment_learning(
    container: Container,
    experiment_id: UUID,
    body: UpdateLearningRequest,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> LearningResponse:
    use_case = container.resolve(UpdateExperimentLearningUseCase)
    try:
        learning = await use_case.execute(experiment_id, body)
    except LearningNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    return LearningResponse.model_validate(learning)
