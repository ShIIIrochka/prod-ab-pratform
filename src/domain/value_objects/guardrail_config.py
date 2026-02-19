from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GuardrailAction(StrEnum):
    """Действие при срабатывании guardrail."""

    PAUSE = "pause"  # Поставить на паузу
    ROLLBACK_TO_CONTROL = "rollback_to_control"  # Откатить к контролю


@dataclass(frozen=True)
class GuardrailConfig:
    metric_key: str
    threshold: float
    observation_window_minutes: int
    action: GuardrailAction

    def __post_init__(self) -> None:
        if self.observation_window_minutes <= 0:
            msg = (
                f"Observation window must be positive, "
                f"got {self.observation_window_minutes}"
            )
            raise ValueError(msg)
