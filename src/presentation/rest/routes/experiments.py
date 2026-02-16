from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status

from src.application.dto.experiment import (
    ApproveExperimentRequest,
    CompleteExperimentRequest,
    ExperimentCreateRequest,
    ExperimentListResponse,
    ExperimentResponse,
    ExperimentUpdateRequest,
    RejectExperimentRequest,
    RequestChangesRequest,
)
from src.application.dto.user import UserResponse
from src.application.usecases import (
    ApproveExperimentUseCase,
    CompleteExperimentUseCase,
    CreateExperimentUseCase,
    GetExperimentUseCase,
    LaunchExperimentUseCase,
    ListExperimentsUseCase,
    PauseExperimentUseCase,
    RejectExperimentUseCase,
    RequestChangesUseCase,
    ResumeExperimentUseCase,
    SendExperimentToReviewUseCase,
    UpdateExperimentUseCase,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import (
    Container,
    require_roles,
)
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/experiments",
    tags=["Experiments"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_experiment(
    data: ExperimentCreateRequest,
    container: Container,
    current_user: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(CreateExperimentUseCase)
    experiment = await use_case.execute(data, current_user.id)
    return ExperimentResponse.model_validate(experiment)


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    container: Container,
    flag_key: str | None = None,
    status: ExperimentStatus | None = None,
) -> ExperimentListResponse:
    use_case = container.resolve(ListExperimentsUseCase)
    experiments = await use_case.execute(flag_key=flag_key, status=status)
    return ExperimentListResponse(
        experiments=[ExperimentResponse.model_validate(e) for e in experiments]
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: UUID,
    container: Container,
) -> ExperimentResponse:
    use_case = container.resolve(GetExperimentUseCase)
    experiment = await use_case.execute(experiment_id)
    return ExperimentResponse.model_validate(experiment)


@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: UUID,
    data: ExperimentUpdateRequest,
    container: Container,
    _: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(UpdateExperimentUseCase)
    experiment = await use_case.execute(experiment_id, data)
    return ExperimentResponse.model_validate(experiment)


@router.post(
    "/{experiment_id}/send-to-review", response_model=ExperimentResponse
)
async def send_to_review(
    experiment_id: UUID,
    container: Container,
    _: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(SendExperimentToReviewUseCase)
    experiment = await use_case.execute(experiment_id)
    return ExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/approve", response_model=ExperimentResponse)
async def approve_experiment(
    experiment_id: UUID,
    data: ApproveExperimentRequest,
    container: Container,
    current_user: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.APPROVER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(ApproveExperimentUseCase)
    experiment = await use_case.execute(experiment_id, current_user.id, data)
    return ExperimentResponse.model_validate(experiment)


@router.post(
    "/{experiment_id}/request-changes", response_model=ExperimentResponse
)
async def request_changes(
    experiment_id: UUID,
    data: RequestChangesRequest,
    container: Container,
    current_user: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.APPROVER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(RequestChangesUseCase)
    experiment = await use_case.execute(experiment_id, current_user.id, data)
    return ExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/reject", response_model=ExperimentResponse)
async def reject_experiment(
    experiment_id: UUID,
    data: RejectExperimentRequest,
    container: Container,
    current_user: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.APPROVER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(RejectExperimentUseCase)
    experiment = await use_case.execute(experiment_id, current_user.id, data)
    return ExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/launch", response_model=ExperimentResponse)
async def launch_experiment(
    experiment_id: UUID,
    container: Container,
    current_user: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(LaunchExperimentUseCase)
    experiment = await use_case.execute(experiment_id, current_user.id)
    return ExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/pause", response_model=ExperimentResponse)
async def pause_experiment(
    experiment_id: UUID,
    container: Container,
    _: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(PauseExperimentUseCase)
    experiment = await use_case.execute(experiment_id)
    return ExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/resume", response_model=ExperimentResponse)
async def resume_experiment(
    experiment_id: UUID,
    container: Container,
    _: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(ResumeExperimentUseCase)
    experiment = await use_case.execute(experiment_id)
    return ExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
async def complete_experiment(
    experiment_id: UUID,
    data: CompleteExperimentRequest,
    container: Container,
    current_user: Annotated[
        UserResponse,
        Depends(require_roles([UserRole.ADMIN, UserRole.EXPERIMENTER])),
    ],
) -> ExperimentResponse:
    use_case = container.resolve(CompleteExperimentUseCase)
    experiment = await use_case.execute(
        experiment_id, UUID(current_user.id), data
    )
    return ExperimentResponse.model_validate(experiment)
