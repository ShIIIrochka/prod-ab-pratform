from __future__ import annotations

from uuid import UUID

from src.application.dto.learnings import UpdateLearningRequest
from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.domain.aggregates.learning import Learning
from src.domain.exceptions.learnings import LearningNotFoundError


class UpdateExperimentLearningUseCase:
    def __init__(self, learnings_repository: LearningsRepositoryPort) -> None:
        self._learnings_repository = learnings_repository

    async def execute(
        self,
        experiment_id: UUID,
        data: UpdateLearningRequest,
    ) -> Learning:
        learning = await self._learnings_repository.get_by_experiment_id(
            experiment_id
        )
        if not learning:
            raise LearningNotFoundError(
                f"Learning record not found for experiment {experiment_id}"
            )
        updated = learning.with_updated_editable(
            hypothesis=data.hypothesis,
            context_and_segment=data.context_and_segment,
            links=data.links,
            notes=data.notes,
            tags=data.tags,
        )
        await self._learnings_repository.update_learning(updated)
        learning = await self._learnings_repository.get_by_experiment_id(
            experiment_id
        )
        if not learning:
            raise LearningNotFoundError(
                f"Learning record not found for experiment {experiment_id}"
            )
        return learning
