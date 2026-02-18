from __future__ import annotations

from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.domain.aggregates.event_type import EventType


class ListEventTypesUseCase:
    def __init__(
        self,
        event_types_repository: EventTypesRepositoryPort,
    ) -> None:
        self._event_types_repository = event_types_repository

    async def execute(self) -> list[EventType]:
        return await self._event_types_repository.list_all()
