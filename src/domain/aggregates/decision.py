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
    variant_id: UUID | None
    variant_name: str | None
    experiment_version: int | None
    timestamp: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.experiment_id and not self.variant_id:
            msg = "Variant ID is required when experiment ID is set"
            raise ValueError(msg)

    def is_from_experiment(self) -> bool:
        return self.experiment_id is not None
