from __future__ import annotations

from abc import ABC, abstractmethod

from domain.aggregates.feature_flag import FeatureFlag


class FeatureFlagsRepositoryPort(ABC):
    @abstractmethod
    async def get_by_key(self, flag_key: str) -> FeatureFlag | None:
        raise NotImplementedError
