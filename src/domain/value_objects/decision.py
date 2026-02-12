from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Decision:
    decision_id: str
    subject_id: str
    flag_key: str
    value: str | int | float | bool
    experiment_id: str | None
    variant_id: str | None
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.experiment_id and not self.variant_id:
            msg = "Variant ID is required when experiment ID is set"
            raise ValueError(msg)

    def is_from_experiment(self) -> bool:
        """Проверяет, выдано ли решение из эксперимента."""
        return self.experiment_id is not None
