from __future__ import annotations

import hashlib

from datetime import UTC, datetime, timedelta

from src.domain.aggregates.decision import Decision
from src.domain.aggregates.experiment import Experiment


def _deterministic_probability_check(
    subject_id: str, seed: str, probability: float
) -> bool:
    if probability >= 1.0:
        return True
    if probability <= 0.0:
        return False

    seed_str = f"{subject_id}:{seed}"
    h = hashlib.sha256(seed_str.encode()).hexdigest()
    bucket = int(h[:16], 16) / (16**16)
    return bucket < probability


def check_participation_allowed(
    subject_id: str,
    experiment: Experiment,
    active_experiments: list[Experiment],
    recent_decisions: list[Decision],
    current_time: datetime,
    max_concurrent_experiments: int,
    cooldown_period_days: int,
    experiments_before_cooldown: int,
    cooldown_experiment_probability: float,
) -> tuple[bool, str | None]:
    other_active = [
        exp for exp in active_experiments if exp.id != experiment.id
    ]

    if len(other_active) >= max_concurrent_experiments:
        competing = other_active + [experiment]
        competing_sorted = sorted(
            competing, key=lambda e: e.created_at, reverse=True
        )
        top_experiments = competing_sorted[:max_concurrent_experiments]
        if experiment not in top_experiments:
            return (
                False,
                f"User already participates in {len(other_active)} experiments "
                f"(limit: {max_concurrent_experiments}), "
                f"experiment has lower priority",
            )

    cooldown_threshold = current_time - timedelta(days=cooldown_period_days)
    recent_experiment_participations = [
        d
        for d in recent_decisions
        if d.is_from_experiment()
        and d.timestamp >= cooldown_threshold.replace(tzinfo=UTC)
        and d.experiment_id != experiment.id
    ]

    if len(recent_experiment_participations) >= experiments_before_cooldown:
        adjusted_cooldown_probability = max(
            cooldown_experiment_probability, experiment.audience_fraction
        )
        seed = f"cooldown:{experiment.id}:{current_time.date()}"
        cooldown_check_result = _deterministic_probability_check(
            subject_id, seed, adjusted_cooldown_probability
        )
        if not cooldown_check_result:
            return (
                False,
                f"User in cooldown period "
                f"({len(recent_experiment_participations)} recent participations)",
            )

    return True, None
