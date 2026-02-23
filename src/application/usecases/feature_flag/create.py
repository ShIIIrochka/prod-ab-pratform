from __future__ import annotations

from src.application.dto.feature_flag import FeatureFlagCreateRequest
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.feature_flag import FeatureFlag
from src.domain.exceptions import FeatureFlagAlreadyExistsError


class CreateFeatureFlagUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository
        self._uow = uow

    async def execute(self, data: FeatureFlagCreateRequest) -> FeatureFlag:
        existing = await self._feature_flags_repository.get_by_key(data.key)
        if existing:
            raise FeatureFlagAlreadyExistsError

        flag = FeatureFlag(
            key=data.key,
            value_type=data.value_type,
            default_value=data.default_value,
            description=data.description,
        )
        try:
            async with self._uow:
                await self._feature_flags_repository.save(flag)
            return flag
        except ValueError:
            raise FeatureFlagAlreadyExistsError
