from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from src.domain.aggregates.experiment import Experiment


@dataclass(frozen=True)
class ExperimentVersion:
    version: int
    changed_at: datetime
    changed_by: str | None
    snapshot: dict


def experiment_to_snapshot(experiment: Experiment) -> dict:
    """Serialize an Experiment aggregate to a JSON-safe dict for storage.

    All UUID/enum/datetime values are converted to strings so the result
    can be stored as JSONB without further processing.
    """

    def _str(v: object) -> str:
        return str(v)

    def _iso(v: datetime) -> str:
        return v.isoformat()

    def _variant(v: object) -> dict:
        from src.domain.entities.variant import Variant

        assert isinstance(v, Variant)
        return {
            "id": _str(v.id),
            "name": v.name,
            "value": v.value,
            "weight": v.weight,
            "is_control": v.is_control,
        }

    def _guardrail(g: object) -> dict:
        from src.domain.entities.guardrail_config import GuardrailConfig

        assert isinstance(g, GuardrailConfig)
        return {
            "id": _str(g.id),
            "metric_key": g.metric_key,
            "threshold": g.threshold,
            "observation_window_minutes": g.observation_window_minutes,
            "action": g.action.value,
        }

    def _approval(a: object) -> dict:
        from src.domain.value_objects.approval import Approval

        assert isinstance(a, Approval)
        return {
            "user_id": a.user_id,
            "comment": a.comment,
            "timestamp": _iso(a.timestamp),
        }

    def _completion(c: object) -> dict | None:
        if c is None:
            return None
        from src.domain.value_objects.experiment_completion import (
            ExperimentCompletion,
        )

        assert isinstance(c, ExperimentCompletion)
        return {
            "outcome": c.outcome.value,
            "winner_variant_id": _str(c.winner_variant_id)
            if c.winner_variant_id
            else None,
            "comment": c.comment,
            "completed_at": _iso(c.completed_at),
            "completed_by": c.completed_by,
        }

    def _targeting_rule(tr: object) -> dict | None:
        if tr is None:
            return None
        from src.domain.value_objects.targeting_rule import TargetingRule

        assert isinstance(tr, TargetingRule)
        return {"rule_expression": tr.rule_expression}

    return {
        "id": _str(experiment.id),
        "flag_key": experiment.flag_key,
        "name": experiment.name,
        "status": experiment.status.value,
        "version": experiment.version,
        "audience_fraction": experiment.audience_fraction,
        "variants": [_variant(v) for v in experiment.variants],
        "targeting_rule": _targeting_rule(experiment.targeting_rule),
        "owner_id": experiment.owner_id,
        "target_metric_key": experiment.target_metric_key,
        "metric_keys": list(experiment.metric_keys),
        "approvals": [_approval(a) for a in experiment.approvals],
        "guardrails": [_guardrail(g) for g in experiment.guardrails],
        "completion": _completion(experiment.completion),
        "rollback_to_control_active": experiment.rollback_to_control_active,
        "created_at": _iso(experiment.created_at),
        "updated_at": _iso(experiment.updated_at),
    }
