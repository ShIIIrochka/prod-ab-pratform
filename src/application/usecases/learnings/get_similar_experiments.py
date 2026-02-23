from __future__ import annotations

from src.application.dto.learnings import GetSimilarCriteria
from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.domain.aggregates.experiment import Experiment


class GetSimilarExperimentsUseCase:
    def __init__(self, learnings_repository: LearningsRepositoryPort) -> None:
        self._learnings_repository = learnings_repository

    async def execute(self, criteria: GetSimilarCriteria) -> list[Experiment]:
        return await self._learnings_repository.get_similar(criteria)
