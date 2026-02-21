from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExperimentOutcome(StrEnum):
    ROLLOUT_WINNER = "rollout_winner"
    ROLLBACK = "rollback"
    NO_EFFECT = "no_effect"


@dataclass(frozen=True)
class ExperimentCompletion:
    outcome: ExperimentOutcome
    winner_variant_id: str | None
    comment: str
    completed_at: datetime
    completed_by: str

    def __post_init__(self) -> None:
        if (
            self.outcome == ExperimentOutcome.ROLLOUT_WINNER
            and not self.winner_variant_id
        ):
            msg = "Winner variant ID is required for ROLLOUT_WINNER outcome"
            raise ValueError(msg)
        if (
            self.outcome != ExperimentOutcome.ROLLOUT_WINNER
            and self.winner_variant_id
        ):
            msg = "Winner variant ID should only be set for ROLLOUT_WINNER outcome"
            raise ValueError(msg)
