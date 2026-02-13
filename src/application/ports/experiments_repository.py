from __future__ import annotations

from abc import ABC, abstractmethod

from domain.aggregates.experiment import Experiment


class ExperimentsRepositoryPort(ABC):
    @abstractmethod
    def get_active_by_flag_key(self, flag_key: str) -> Experiment | None:
        raise NotImplementedError
