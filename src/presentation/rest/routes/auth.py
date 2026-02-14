from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from starlette.authentication import requires

from application.dto.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from application.dto.user import UserResponse
from application.usecases.auth.login import LoginUseCase
from application.usecases.user.create import CreateUserUseCase
from presentation.rest.dependencies import Container, get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@requires(["authenticated", "admin"])
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    container: Container,
) -> UserResponse:
    use_case = container.resolve(CreateUserUseCase)
    user = await use_case.execute(data)
    return UserResponse.from_domain(user)


@requires(["authenticated"])
@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    container: Container,
) -> TokenResponse:
    use_case = container.resolve(LoginUseCase)
    response = await use_case.execute(data)
    return TokenResponse.from_domain(response)


@requires(["authenticated"])
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    return current_user
