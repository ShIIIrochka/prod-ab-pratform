from __future__ import annotations

from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.domain.aggregates.event_type import EventType
from src.domain.exceptions.events import EventTypeNotFoundError


class GetEventTypeUseCase:
    def __init__(
        self,
        event_types_repository: EventTypesRepositoryPort,
    ) -> None:
        self._event_types_repository = event_types_repository

    async def execute(self, key: str) -> EventType:
        event_type = await self._event_types_repository.get_by_key(key)

        if event_type is None:
            raise EventTypeNotFoundError(key)

        return event_type
