"""Агрегат Metric - каталог метрик."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metric:
    """Метрика для оценки экспериментов.

    Агрегат-корень для управления метриками.
    """

    key: str
    name: str
    calculation_rule: str  # Правило вычисления (DSL или JSON)
    requires_exposure: bool = False
    description: str | None = None

    def __post_init__(self) -> None:
        """Валидация метрики."""
        if not self.key:
            msg = "Metric key cannot be empty"
            raise ValueError(msg)
        if not self.name:
            msg = "Metric name cannot be empty"
            raise ValueError(msg)
        if not self.calculation_rule:
            msg = "Calculation rule cannot be empty"
            raise ValueError(msg)
