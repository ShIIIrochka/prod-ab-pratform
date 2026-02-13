from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.aggregates import BaseEntity


@dataclass
class Decision(BaseEntity):
    """Решение о том, какое значение показать пользователю.

    Соответствует Decision API из ТЗ (раздел 3.3):
    - decision_id (через property) - служебный идентификатор решения
    - flag_key - запрошенный флаг
    - value - итоговое значение (из варианта или default)
    - experiment_id - UUID эксперимента (если применился)
    - variant_id - ID варианта (variant.name, если применился)
    - experiment_version - версия эксперимента на момент решения
    - subject_id - идентификатор субъекта (строка по ТЗ 3.2)
    - timestamp - время принятия решения
    """

    subject_id: str  # Строка по ТЗ 3.2: "идентификатор субъекта"
    flag_key: str
    value: str | int | float | bool
    experiment_id: UUID | None
    variant_id: str | None
    experiment_version: int | None
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.experiment_id and not self.variant_id:
            msg = "Variant ID is required when experiment ID is set"
            raise ValueError(msg)

    @property
    def decision_id(self) -> str:
        """Служебный идентификатор решения для связывания с событиями (ТЗ 3.3)."""
        return str(self.id)

    def is_from_experiment(self) -> bool:
        """Проверяет, выдано ли решение из эксперимента."""
        return self.experiment_id is not None
