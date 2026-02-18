from __future__ import annotations

from src.application.dto.event_type import EventTypeCreateRequest
from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.event_type import EventType


class CreateEventTypeUseCase:
    def __init__(
        self,
        event_types_repository: EventTypesRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._event_types_repository = event_types_repository
        self._uow = uow

    async def execute(self, data: EventTypeCreateRequest) -> EventType:
        event_type = EventType(
            key=data.key,
            name=data.name,
            description=data.description,
            required_params=data.required_params,
            requires_exposure=data.requires_exposure,
        )

        async with self._uow:
            await self._event_types_repository.save(event_type)

        return event_type
