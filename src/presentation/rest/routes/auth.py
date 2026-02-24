from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Security, status

from src.application.dto.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.application.dto.user import UserResponse
from src.application.usecases import GetUserByIdUseCase
from src.application.usecases.auth.login import LoginUseCase
from src.application.usecases.user.create import CreateUserUseCase
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import Container, require_roles
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Security(JWTBackend.auth_required),
        Depends(require_roles([UserRole.ADMIN])),
    ],
)
async def register(
    data: RegisterRequest,
    container: Container,
) -> UserResponse:
    use_case = container.resolve(CreateUserUseCase)
    user = await use_case.execute(data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    container: Container,
) -> TokenResponse:
    use_case = container.resolve(LoginUseCase)
    response = await use_case.execute(data)
    return TokenResponse.model_validate(response)


@router.get(
    "/me",
    dependencies=[Security(JWTBackend.auth_required)],
    response_model=UserResponse,
)
async def get_me(
    request: Request,
    container: Container,
) -> UserResponse:
    use_case = container.resolve(GetUserByIdUseCase)
    user = await use_case.execute(request.user.id)
    return UserResponse.model_validate(user)
