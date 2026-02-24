from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.aggregates.learning import Learning
from src.domain.value_objects.experiment_completion import (
    ExperimentOutcome,
)


class LearningsRepositoryPort(ABC):
    @abstractmethod
    async def save(self, learning: Learning) -> None:
        """Сохранить или перезаписать запись в базе знаний (при complete)."""
        raise NotImplementedError

    @abstractmethod
    async def update_learning(self, learning: Learning) -> None:
        """Обновить редактируемые поля существующей записи. Raises if not found."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_experiment_id(
        self,
        experiment_id: UUID,
    ) -> Learning | None:
        """Вернуть Learning по experiment_id или None."""
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
    ) -> list[Learning]:
        raise NotImplementedError
