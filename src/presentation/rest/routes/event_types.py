from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Security, status

from src.application.dto.event_type import (
    EventTypeCreateRequest,
    EventTypeListResponse,
    EventTypeResponse,
)
from src.application.usecases.event_type.create import CreateEventTypeUseCase
from src.application.usecases.event_type.get import GetEventTypeUseCase
from src.application.usecases.event_type.list import ListEventTypesUseCase
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import Container, require_roles
from src.presentation.rest.middlewares import AuthUser, JWTBackend


router = APIRouter(
    prefix="/event-types",
    tags=["Event Types"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.post(
    "",
    response_model=EventTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_type(
    data: EventTypeCreateRequest,
    container: Container,
    _: Annotated[AuthUser, Depends(require_roles([UserRole.ADMIN]))],
) -> EventTypeResponse:
    use_case = container.resolve(CreateEventTypeUseCase)
    event_type = await use_case.execute(data)
    return EventTypeResponse.model_validate(event_type)


@router.get("", response_model=EventTypeListResponse)
async def list_event_types(
    container: Container,
) -> EventTypeListResponse:
    use_case = container.resolve(ListEventTypesUseCase)
    event_types = await use_case.execute()
    return EventTypeListResponse(
        event_types=[EventTypeResponse.model_validate(et) for et in event_types]
    )


@router.get("/{key}", response_model=EventTypeResponse)
async def get_event_type(
    key: str,
    container: Container,
) -> EventTypeResponse:
    use_case = container.resolve(GetEventTypeUseCase)
    event_type = await use_case.execute(key)
    return EventTypeResponse.model_validate(event_type)
