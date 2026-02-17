from __future__ import annotations

import hashlib

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_status import ExperimentStatus


def _stable_hash_bucket(
    subject_id: str, experiment_id: str, version: int
) -> float:
    """Детерминированно отображает (subject_id, experiment_id, version) в число в [0, 1).

    Использует первые 8 байт хеша SHA256 для получения равномерно распределенного
    значения в диапазоне [0, 1). Использует байты напрямую для избежания проблем
    с точностью float при работе с очень большими числами.
    """
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
) -> DecisionResult:
    """Принимает решение о том, какой вариант показать пользователю.

    Args:
        experiment: Эксперимент (может быть None)
        subject_id: Идентификатор пользователя
        attributes: Атрибуты для таргетинга

    Returns:
        DecisionResult с информацией о том, применился ли эксперимент,
        значение и variant_id (если применился).
    """
    # Если эксперимента нет или он не в статусе RUNNING - не применяется
    if experiment is None or experiment.status != ExperimentStatus.RUNNING:
        return DecisionResult(applied=False, value="", variant_id=None)

    # Проверяем таргетинг
    if experiment.targeting_rule is not None:
        if not experiment.targeting_rule.evaluate(attributes):
            return DecisionResult(applied=False, value="", variant_id=None)

    # Проверяем попадание в аудиторию эксперимента
    bucket = _stable_hash_bucket(
        subject_id, str(experiment.id), experiment.version
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
            subject_id, experiment, variants_sorted, cumulative
        )

    return DecisionResult(
        applied=True,
        value=variant.value,
        variant_id=variant.id,
        variant_name=variant.name,
    )
