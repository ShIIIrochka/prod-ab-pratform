from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Security, status

from src.application.dto.feature_flag import (
    FeatureFlagCreateRequest,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdateDefaultRequest,
)
from src.application.dto.user import UserResponse
from src.application.usecases.feature_flag.create import (
    CreateFeatureFlagUseCase,
)
from src.application.usecases.feature_flag.get import GetFeatureFlagUseCase
from src.application.usecases.feature_flag.list import ListFeatureFlagsUseCase
from src.application.usecases.feature_flag.update import (
    UpdateFeatureFlagDefaultValueUseCase,
)
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import (
    Container,
    require_roles,
)
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/feature-flags",
    tags=["Feature Flags"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.post(
    "",
    response_model=FeatureFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feature_flag(
    data: FeatureFlagCreateRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> FeatureFlagResponse:
    use_case = container.resolve(CreateFeatureFlagUseCase)
    flag = await use_case.execute(data)
    return FeatureFlagResponse.model_validate(flag)


@router.get("", response_model=FeatureFlagListResponse)
async def list_feature_flags(
    container: Container,
) -> FeatureFlagListResponse:
    use_case = container.resolve(ListFeatureFlagsUseCase)
    flags = await use_case.execute()
    return FeatureFlagListResponse(
        flags=[FeatureFlagResponse.model_validate(f) for f in flags]
    )


@router.get("/{key}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    key: str,
    container: Container,
) -> FeatureFlagResponse:
    use_case = container.resolve(GetFeatureFlagUseCase)
    flag = await use_case.execute(key)
    return FeatureFlagResponse.model_validate(flag)


@router.patch("/{key}", response_model=FeatureFlagResponse)
async def update_feature_flag_default(
    key: str,
    data: FeatureFlagUpdateDefaultRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> FeatureFlagResponse:
    use_case = container.resolve(UpdateFeatureFlagDefaultValueUseCase)
    flag = await use_case.execute(key, data)
    return FeatureFlagResponse.model_validate(flag)
