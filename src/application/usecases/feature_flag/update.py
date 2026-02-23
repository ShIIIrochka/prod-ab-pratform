from __future__ import annotations

from src.application.dto.feature_flag import FeatureFlagUpdateDefaultRequest
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.domain.aggregates.feature_flag import FeatureFlag
from src.domain.exceptions.decision import FeatureFlagNotFoundError
from src.domain.exceptions.feature_flags import FeatureFlagAlreadyExistsError


class UpdateFeatureFlagDefaultValueUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository

    async def execute(
        self, key: str, data: FeatureFlagUpdateDefaultRequest
    ) -> FeatureFlag:
        flag = await self._feature_flags_repository.get_by_key(key)
        if not flag:
            raise FeatureFlagNotFoundError

        flag.update_default_value(data.default_value)
        try:
            await self._feature_flags_repository.save(flag)
        except ValueError:
            raise FeatureFlagAlreadyExistsError
        return flag
