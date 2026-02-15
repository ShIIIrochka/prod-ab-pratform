from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.aggregates import BaseEntity


@dataclass
class Decision(BaseEntity):
    subject_id: str
    flag_key: str
    value: str | int | float | bool
    experiment_id: UUID | None
    variant_id: str | None
    experiment_version: int | None
    timestamp: datetime = datetime.utcnow()

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
