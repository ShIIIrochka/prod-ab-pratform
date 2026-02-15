from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.aggregates.decision import Decision


class DecisionsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, decision: Decision) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, decision_id: str) -> Decision | None:
        raise NotImplementedError
