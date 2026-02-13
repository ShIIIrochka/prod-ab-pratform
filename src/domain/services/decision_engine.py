from __future__ import annotations

import hashlib

from typing import Any

from domain.aggregates.experiment import Experiment
from domain.entities.variant import Variant


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


def compute_decision_value(
    experiment: Experiment,
    subject_id: str,
    attributes: dict[str, Any],
) -> str | int | float | bool | None:
    if experiment.targeting_rule is None or experiment.targeting_rule.evaluate(
        attributes
    ):
        bucket = _stable_hash_bucket(
            subject_id, str(experiment.id), experiment.version
        )
        if bucket < experiment.audience_fraction:
            variants_sorted = sorted(experiment.variants, key=lambda v: v.name)
            cumulative = _build_cumulative_weights(variants_sorted)
            variant = _select_variant_by_weights(
                subject_id, experiment, variants_sorted, cumulative
            )
            value = variant.value

            return value
    return None
