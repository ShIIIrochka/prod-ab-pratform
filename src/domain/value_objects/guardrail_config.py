from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class GuardrailAction(StrEnum):
    """Действие при срабатывании guardrail."""

    PAUSE = "pause"
    ROLLBACK_TO_CONTROL = "rollback_to_control"


@dataclass(frozen=True)
class GuardrailConfig:
    metric_key: str
    threshold: float
    observation_window_minutes: int
    action: GuardrailAction
    # id is None when the config has just been constructed in domain logic
    # (before being persisted); always populated when loaded from the repository.
    id: UUID | None = field(default=None)

    def __post_init__(self) -> None:
        if self.observation_window_minutes <= 0:
            msg = (
                f"Observation window must be positive, "
                f"got {self.observation_window_minutes}"
            )
            raise ValueError(msg)
