from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from punq import Container as PunqContainer
from starlette.requests import Request

from application.dto.user import UserResponse
from application.usecases.user.get_by_id import GetUserByIdUseCase
from domain.exceptions.users import UserNotFoundError
from infra.bootstrap import create_container


container = create_container()
Container = Annotated[PunqContainer, Depends(lambda: container)]


async def get_current_user(
    container: Container,
    request: Request,
) -> UserResponse:
    if not request.user.is_authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user_id = request.user.payload["user_id"]
    try:
        usecase: GetUserByIdUseCase = container.resolve(GetUserByIdUseCase)
        user = await usecase.execute(user_id)
        return UserResponse.from_domain(user)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
