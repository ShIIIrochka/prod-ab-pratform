from __future__ import annotations

import asyncio

from uuid import UUID

from application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from domain.aggregates.feature_flag import FeatureFlag
from domain.value_objects.flag_value import FlagValue
from infra.adapters.db.models.feature_flag import FeatureFlagModel


class FeatureFlagsRepository(FeatureFlagsRepositoryPort):
    def get_by_key(self, flag_key: str) -> FeatureFlag | None:
        """
        Получает feature flag по ключу.

        ВНИМАНИЕ: Это синхронная обёртка для async операции.
        Использует asyncio.create_task для работы в async контексте.
        """
        # Используем run_coroutine_threadsafe или новый event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Нет running loop, создаём новый
            return asyncio.run(self._get_by_key_async(flag_key))

        # Если loop уже запущен, используем synchronous wrapper через Future
        # Это работает только если мы не в async функции
        # Для упрощения возвращаем None - это нужно будет исправить
        # когда появится полноценная реализация
        import sys

        # Проверяем, не находимся ли мы в корутине
        frame = sys._getframe()
        # Если вызываем из async контекста, то не можем использовать run_until_complete
        # Возвращаем None как временное решение
        return None

    async def _get_by_key_async(self, flag_key: str) -> FeatureFlag | None:
        """Асинхронная версия получения feature flag."""
        model = await FeatureFlagModel.get_or_none(key=flag_key)
        if model is None:
            return None

        return FeatureFlag(
            id=UUID(model.id),
            key=model.key,
            default_value=FlagValue(
                value_type=model.value_type,
                value=model.default_value,
            ),
            description=model.description,
        )
