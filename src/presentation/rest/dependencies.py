from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from punq import Container as PunqContainer
from starlette.requests import Request

from src.application.dto.user import UserResponse
from src.domain.value_objects.user_role import UserRole
from src.infra.bootstrap import create_container


container = create_container()
Container = Annotated[PunqContainer, Depends(lambda: container)]


def require_roles(roles: list[UserRole]) -> Callable:
    async def _check_role(
        request: Request,
    ) -> UserResponse:
        if request.user.is_authenticated and request.user.role not in [
            r.value for r in roles
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return request.user

    return _check_role
