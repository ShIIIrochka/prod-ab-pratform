from __future__ import annotations

from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.domain.aggregates.feature_flag import FeatureFlag
from src.infra.adapters.db.models.feature_flag import FeatureFlagModel


class FeatureFlagsRepository(FeatureFlagsRepositoryPort):
    async def get_by_key(self, flag_key: str) -> FeatureFlag | None:
        model = await FeatureFlagModel.get_or_none(key=flag_key)
        if model is None:
            return None
        return model.to_domain()

    async def save(self, flag: FeatureFlag) -> None:
        model = FeatureFlagModel.from_domain(flag)
        await model.save()

    async def list_all(self) -> list[FeatureFlag]:
        models = await FeatureFlagModel.all()
        return [m.to_domain() for m in models]
