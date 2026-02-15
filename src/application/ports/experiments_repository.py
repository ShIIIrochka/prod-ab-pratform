from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.aggregates.experiment import Experiment


class ExperimentsRepositoryPort(ABC):
    @abstractmethod
    async def get_active_by_flag_key(self, flag_key: str) -> Experiment | None:
        raise NotImplementedError
