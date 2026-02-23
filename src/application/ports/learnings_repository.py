from __future__ import annotations

from abc import ABC, abstractmethod

from src.application.dto.learnings import GetSimilarCriteria
from src.domain.aggregates.experiment import Experiment


class LearningsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, experiment: Experiment) -> None:
        """Save or update the experiment as a learning document (only if completed)."""
        raise NotImplementedError

    @abstractmethod
    async def get_similar(
        self, criteria: GetSimilarCriteria
    ) -> list[Experiment]:
        """Return domain experiments matching search criteria; empty list if none."""
        raise NotImplementedError
