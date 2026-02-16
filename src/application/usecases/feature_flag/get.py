from __future__ import annotations

from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.domain.aggregates.feature_flag import FeatureFlag
from src.domain.exceptions.decision import FeatureFlagNotFoundError


class GetFeatureFlagUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository

    async def execute(self, key: str) -> FeatureFlag:
        flag = await self._feature_flags_repository.get_by_key(key)
        if not flag:
            raise FeatureFlagNotFoundError
        return flag
