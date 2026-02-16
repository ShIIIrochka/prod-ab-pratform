from __future__ import annotations

from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.domain.aggregates.feature_flag import FeatureFlag


class ListFeatureFlagsUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository

    async def execute(self) -> list[FeatureFlag]:
        return await self._feature_flags_repository.list_all()
