from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.entities.guardrail_config import GuardrailAction


@dataclass(frozen=True)
class GuardrailTrigger:
    """Запись о срабатывании guardrail."""

    experiment_id: UUID
    metric_key: str
    threshold: float
    observation_window_minutes: int
    action: GuardrailAction
    actual_value: float
    triggered_at: datetime
    # id is None when just constructed; populated when loaded from the repository.
    id: UUID | None = field(default=None)

    def __post_init__(self) -> None:
        if self.experiment_id is None:
            msg = "Experiment ID cannot be empty"
            raise ValueError(msg)
