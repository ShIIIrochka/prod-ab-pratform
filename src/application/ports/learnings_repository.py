from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_completion import (
    ExperimentOutcome,
)


class LearningsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, experiment: Experiment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_similar(
        self,
        limit: int,
        query: str | None = None,
        flag_key: str | None = None,
        owner_id: str | None = None,
        outcome: ExperimentOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        target_metric_key: str | None = None,
    ) -> list[Experiment]:
        raise NotImplementedError
