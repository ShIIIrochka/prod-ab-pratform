from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.aggregates import BaseEntity
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.guardrail_config import GuardrailConfig
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_completion import (
    ExperimentOutcome,
)
from src.domain.value_objects.targeting_rule import TargetingRule


@dataclass
class Learning(BaseEntity):
    experiment_id: UUID
    hypothesis: str | None
    context_and_segment: str | None
    links: list[str] | None
    notes: str | None
    tags: list[str] | None
    completed_by: str
    owner_id: str
    flag_key: str
    name: str
    outcome_comment: str
    audience_fraction: float
    target_metric_key: str | None = None
    metric_keys: list[str] = field(default_factory=list)
    guardrails: list[GuardrailConfig] = field(default_factory=list)
    outcome: ExperimentOutcome = ExperimentOutcome.NO_EFFECT
    winner_variant_id: str | None = None
    completed_at: datetime = field(default_factory=datetime.utcnow)
    variants: list[Variant] = field(default_factory=list)
    targeting_rule: TargetingRule | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_completed_experiment(cls, experiment: Experiment) -> Learning:
        if not experiment.completion:
            raise ValueError(
                "Experiment must have completion to create Learning"
            )
        c = experiment.completion
        return cls(
            experiment_id=experiment.id,
            hypothesis="",
            context_and_segment="",
            links=None,
            notes=None,
            tags=None,
            flag_key=experiment.flag_key,
            name=experiment.name,
            target_metric_key=experiment.target_metric_key,
            metric_keys=experiment.metric_keys or [],
            guardrails=list(experiment.guardrails),
            outcome=c.outcome,
            outcome_comment=c.comment,
            winner_variant_id=c.winner_variant_id,
            completed_at=c.completed_at,
            completed_by=c.completed_by,
            owner_id=experiment.owner_id,
            audience_fraction=experiment.audience_fraction,
            variants=list(experiment.variants),
            targeting_rule=experiment.targeting_rule,
            created_at=experiment.created_at,
            updated_at=experiment.updated_at,
        )

    @classmethod
    def with_updated_editable(
        cls,
        hypothesis: str | None = None,
        context_and_segment: str | None = None,
        links: list[str] | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> Learning:
        return cls(
            experiment_id=cls.experiment_id,
            hypothesis=hypothesis,
            context_and_segment=context_and_segment,
            links=links,
            notes=notes,
            tags=tags,
            flag_key=cls.flag_key,
            name=cls.name,
            target_metric_key=cls.target_metric_key,
            metric_keys=cls.metric_keys,
            guardrails=cls.guardrails,
            outcome=cls.outcome,
            outcome_comment=cls.outcome_comment,
            winner_variant_id=cls.winner_variant_id,
            completed_at=cls.completed_at,
            completed_by=cls.completed_by,
            owner_id=cls.owner_id,
            audience_fraction=cls.audience_fraction,
            variants=cls.variants,
            targeting_rule=cls.targeting_rule,
            created_at=cls.created_at,
            updated_at=cls.updated_at,
        )
