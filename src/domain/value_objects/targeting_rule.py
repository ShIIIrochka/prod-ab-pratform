from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TargetingRule:
    rule_expression: str

    def __post_init__(self) -> None:
        """Валидация выражения правила."""
        if not self.rule_expression.strip():
            msg = "Rule expression cannot be empty string"
            raise ValueError(msg)

    def evaluate(self, attributes: dict[str, Any]) -> bool:
        """Вычисляет правило на основе атрибутов пользователя.

        Args:
            attributes: Атрибуты пользователя (страна, версия и т.д.)

        Returns:
            True если пользователь проходит правило, False иначе.

        Note:
            Реальная реализация парсинга DSL будет в сервисном слое.
            Здесь только структура данных.
        """
        # TODO: Реализовать парсинг DSL выражения
        # Пока возвращаем True для валидного выражения
        return True
