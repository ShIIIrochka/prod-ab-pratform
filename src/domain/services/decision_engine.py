from __future__ import annotations

import hashlib

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_status import ExperimentStatus


def _stable_hash_bucket(
    subject_id: str,
    experiment_id: str,
    version: int,
    epoch: int,
) -> float:
    """Детерминированно отображает (subject_id, experiment_id, version, epoch) в число в [0, 1).

    Использует первые 8 байт хеша SHA256 для получения равномерно распределенного
    значения в диапазоне [0, 1). Использует байты напрямую для избежания проблем
    с точностью float при работе с очень большими числами.
    """
    seed = f"{subject_id}:{experiment_id}:{version}:{epoch}"
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


def _current_epoch(rotation_period_days: int) -> int:
    if rotation_period_days <= 0:
        return 0

    now = datetime.utcnow().timestamp()
    period_seconds = rotation_period_days * 24 * 60 * 60
    return int(now // period_seconds)


def _select_variant_by_weights(
    experiment: Experiment,
    variants_sorted: list[Variant],
    cumulative_weights: list[float],
    bucket: float,
) -> Variant:
    """Выбирает вариант по детерминированному бакету и кумулятивным весам."""
    if bucket >= experiment.audience_fraction:
        return experiment.get_control_variant()
    inner = bucket / experiment.audience_fraction
    total = experiment.audience_fraction
    for i, cum in enumerate(cumulative_weights):
        if inner < cum / total:
            return variants_sorted[i]
    return variants_sorted[-1]


@dataclass
class DecisionResult:
    """Результат принятия решения для одного флага."""

    applied: bool
    value: str | int | float | bool
    variant_id: UUID | None = None
    variant_name: str | None = None


def compute_decision(
    experiment: Experiment | None,
    subject_id: str,
    attributes: dict[str, Any],
    rotation_period_days: int,
) -> DecisionResult:
    epoch = _current_epoch(rotation_period_days)
    # Если эксперимента нет или он не в статусе RUNNING - не применяется
    if experiment is None or experiment.status != ExperimentStatus.RUNNING:
        return DecisionResult(applied=False, value="", variant_id=None)

    # Проверяем таргетинг
    if experiment and experiment.targeting_rule:
        targeting_result = experiment.targeting_rule.evaluate(attributes)
        if not targeting_result:
            return DecisionResult(applied=False, value="", variant_id=None)

    # Проверяем попадание в аудиторию эксперимента
    bucket = _stable_hash_bucket(
        subject_id, str(experiment.id), experiment.version, epoch
    )
    if bucket >= experiment.audience_fraction:
        return DecisionResult(applied=False, value="", variant_id=None)

    # Выбираем вариант
    variants_sorted = sorted(experiment.variants, key=lambda v: v.name)

    # Если включен режим отката к контролю - выбираем control
    if experiment.rollback_to_control_active:
        variant = experiment.get_control_variant()
    else:
        cumulative = _build_cumulative_weights(variants_sorted)
        variant = _select_variant_by_weights(
            experiment, variants_sorted, cumulative, bucket
        )

    return DecisionResult(
        applied=True,
        value=variant.value,
        variant_id=variant.id,
        variant_name=variant.name,
    )
