from __future__ import annotations

import hashlib

from collections.abc import Callable
from datetime import datetime
from typing import Any

from domain.aggregates.experiment import Experiment
from domain.entities.variant import Variant
from domain.value_objects.decision import Decision
from domain.value_objects.experiment_status import ExperimentStatus


def _stable_hash_bucket(
    subject_id: str, experiment_id: str, version: int
) -> float:
    """Детерминированно отображает (subject_id, experiment_id, version) в число в [0, 1)."""
    seed = f"{subject_id}:{experiment_id}:{version}"
    h = hashlib.sha256(seed.encode()).hexdigest()
    return int(h[:16], 16) / (16**16)


def _build_cumulative_weights(variants_sorted: list[Variant]) -> list[float]:
    """Строит кумулятивные веса: result[i] = sum(weight вариантов 0..i).

    Например для вариантов с весами [0.05, 0.05, 0.10] получится [0.05, 0.10, 0.20].
    Нужно, чтобы по числу из [0, 1) однозначно выбрать вариант по долям.
    """
    acc = 0.0
    result = []
    for v in variants_sorted:
        acc += v.weight
        result.append(acc)
    return result


def _select_variant_by_weights(
    subject_id: str,
    experiment: Experiment,
    variants_sorted: list[Variant],
    cumulative_weights: list[float],
) -> Variant:
    """Выбирает вариант по детерминированному бакету и кумулятивным весам."""
    bucket = _stable_hash_bucket(
        subject_id, str(experiment.id), experiment.version
    )
    if bucket >= experiment.audience_fraction:
        return next(v for v in variants_sorted if v.is_control)
    inner = bucket / experiment.audience_fraction
    total = experiment.audience_fraction
    for i, cum in enumerate(cumulative_weights):
        if inner < cum / total:
            return variants_sorted[i]
    return variants_sorted[-1]


def compute_decide_result(
    default_value: str | int | float | bool,
    experiment: Experiment | None,
    subject_id: str,
    attributes: dict[str, Any],
    rollback_active: bool,
    can_participate: bool,
    flag_key: str,
    timestamp: datetime,
    get_decision_id: Callable[[str | None, str | None], str],
) -> Decision:
    value: str | int | float | bool = default_value
    experiment_id: str | None = None
    variant_id: str | None = None

    if (
        experiment is not None
        and experiment.status == ExperimentStatus.RUNNING
        and can_participate
    ):
        if (
            experiment.targeting_rule is None
            or experiment.targeting_rule.evaluate(attributes)
        ):
            bucket = _stable_hash_bucket(
                subject_id, str(experiment.id), experiment.version
            )
            if bucket < experiment.audience_fraction:
                variants_sorted = sorted(
                    experiment.variants, key=lambda v: v.name
                )
                cumulative = _build_cumulative_weights(variants_sorted)
                if rollback_active:
                    variant = experiment.get_control_variant()
                else:
                    variant = _select_variant_by_weights(
                        subject_id, experiment, variants_sorted, cumulative
                    )
                value = variant.value
                experiment_id = str(experiment.id)
                variant_id = variant.name

    decision_id = get_decision_id(experiment_id, variant_id)
    return Decision(
        decision_id=decision_id,
        subject_id=subject_id,
        flag_key=flag_key,
        value=value,
        experiment_id=experiment_id,
        variant_id=variant_id,
        timestamp=timestamp,
    )
