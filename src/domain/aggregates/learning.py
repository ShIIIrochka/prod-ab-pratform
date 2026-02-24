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

    def with_updated_editable(
        self,
        hypothesis: str | None = None,
        context_and_segment: str | None = None,
        links: list[str] | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> Learning:
        if links is not None:
            new_links: list[str] | None = list(links)
        elif self.links is not None:
            new_links = list(self.links)
        else:
            new_links = None

        if tags is not None:
            new_tags: list[str] | None = list(tags)
        elif self.tags is not None:
            new_tags = list(self.tags)
        else:
            new_tags = None

        return Learning(
            id=self.id,
            experiment_id=self.experiment_id,
            hypothesis=hypothesis
            if hypothesis is not None
            else self.hypothesis,
            context_and_segment=(
                context_and_segment
                if context_and_segment is not None
                else self.context_and_segment
            ),
            links=new_links,
            notes=notes if notes is not None else self.notes,
            tags=new_tags,
            completed_by=self.completed_by,
            owner_id=self.owner_id,
            flag_key=self.flag_key,
            name=self.name,
            outcome_comment=self.outcome_comment,
            audience_fraction=self.audience_fraction,
            target_metric_key=self.target_metric_key,
            metric_keys=self.metric_keys,
            guardrails=self.guardrails,
            outcome=self.outcome,
            winner_variant_id=self.winner_variant_id,
            completed_at=self.completed_at,
            variants=self.variants,
            targeting_rule=self.targeting_rule,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
