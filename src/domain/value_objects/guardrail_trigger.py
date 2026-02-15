from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects.guardrail_config import GuardrailAction


@dataclass(frozen=True)
class GuardrailTrigger:
    """Запись о срабатывании guardrail."""

    experiment_id: str
    metric_key: str
    threshold: float
    observation_window_minutes: int
    action: GuardrailAction
    actual_value: float
    triggered_at: datetime

    def __post_init__(self) -> None:
        """Валидация записи о срабатывании."""
        if not self.experiment_id:
            msg = "Experiment ID cannot be empty"
            raise ValueError(msg)
        if not self.metric_key:
            msg = "Metric key cannot be empty"
            raise ValueError(msg)
