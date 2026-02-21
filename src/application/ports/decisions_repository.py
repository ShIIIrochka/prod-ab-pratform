from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.aggregates.decision import Decision


class DecisionsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, decision: Decision) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_many(self, decisions: list[Decision]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, decision_id: UUID) -> Decision | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_ids(self, ids: list[UUID]) -> dict[UUID, Decision]:
        raise NotImplementedError

    @abstractmethod
    async def get_active_experiments_by_subject(
        self, subject_id: str
    ) -> list[Decision]:
        raise NotImplementedError

    @abstractmethod
    async def get_recent_by_subject(
        self,
        subject_id: str,
        since: datetime,
    ) -> list[Decision]:
        raise NotImplementedError
