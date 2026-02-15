from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from src.application.dto.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.application.dto.user import UserResponse
from src.application.usecases.auth.login import LoginUseCase
from src.application.usecases.user.create import CreateUserUseCase
from src.presentation.rest.dependencies import Container, get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
# @requires(["authenticated", "admin"])
async def register(
    data: RegisterRequest,
    container: Container,
) -> UserResponse:
    use_case = container.resolve(CreateUserUseCase)
    user = await use_case.execute(data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
# @requires(["authenticated"])
async def login(
    request: Request,
    data: LoginRequest,
    container: Container,
) -> TokenResponse:
    use_case = container.resolve(LoginUseCase)
    response = await use_case.execute(data)
    return TokenResponse.model_validate(response)


@router.get("/me", response_model=UserResponse)
# @requires(["authenticated"])
async def get_me(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    return current_user
