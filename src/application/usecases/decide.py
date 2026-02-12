from __future__ import annotations

from datetime import datetime
from typing import Any

from domain.ports.decide import (
    ActiveExperimentResolver,
    DecisionIdGenerator,
    FeatureFlagResolver,
    ParticipationPolicy,
)
from domain.services.decision_engine import compute_decide_result
from domain.value_objects.decision import Decision


def decide(
    flag_resolver: FeatureFlagResolver,
    experiment_resolver: ActiveExperimentResolver,
    decision_id_generator: DecisionIdGenerator,
    subject_id: str,
    attributes: dict[str, Any],
    flag_keys: list[str],
    participation_policy: ParticipationPolicy | None = None,
    timestamp: datetime | None = None,
) -> list[Decision]:
    """Возвращает список решений по запрошенным флагам. Порядок совпадает с flag_keys."""
    if not subject_id or not subject_id.strip():
        raise ValueError("subject_id is required and cannot be empty")

    ts = timestamp or datetime.utcnow()
    results: list[Decision] = []
    applied_experiment_ids: list[str] = []

    for flag_key in flag_keys:
        flag = flag_resolver.get_flag(flag_key)
        if flag is None:
            raise ValueError(f"Feature flag not found: {flag_key}")

        experiment, rollback_active = experiment_resolver.get_active_experiment(
            flag_key
        )
        can_participate = True
        if participation_policy is not None and experiment is not None:
            can_participate = participation_policy.can_participate(
                subject_id=subject_id,
                experiment_id=str(experiment.id),
                applied_experiment_ids=applied_experiment_ids,
            )

        def get_decision_id(exp_id: str | None, var_id: str | None) -> str:
            return decision_id_generator.generate(
                subject_id=subject_id,
                flag_key=flag_key,
                experiment_id=exp_id,
                variant_id=var_id,
            )

        decision = compute_decide_result(
            default_value=flag.default_value.value,
            experiment=experiment,
            subject_id=subject_id,
            attributes=attributes,
            rollback_active=rollback_active,
            can_participate=can_participate,
            flag_key=flag_key,
            timestamp=ts,
            get_decision_id=get_decision_id,
        )
        results.append(decision)
        if decision.experiment_id:
            applied_experiment_ids.append(decision.experiment_id)

    return results
