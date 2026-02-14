from __future__ import annotations

from application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from domain.aggregates.feature_flag import FeatureFlag
from infra.adapters.db.models.feature_flag import FeatureFlagModel


class FeatureFlagsRepository(FeatureFlagsRepositoryPort):
    async def get_by_key(self, flag_key: str) -> FeatureFlag | None:
        model = await FeatureFlagModel.get_or_none(key=flag_key)
        if model is None:
            return None
        return model.to_domain()
