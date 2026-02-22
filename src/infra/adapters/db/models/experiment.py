from __future__ import annotations

from datetime import datetime

from tortoise import fields
from tortoise.fields import OnDelete, ReverseRelation
from tortoise.models import Model

from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_completion import (
    ExperimentCompletion,
    ExperimentOutcome,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule
from src.infra.adapters.db.models.approval import ApprovalModel


class ExperimentModel(Model):
    id = fields.UUIDField(pk=True)
    flag_key = fields.CharField(max_length=255, index=True)
    name = fields.CharField(max_length=255)
    status = fields.CharEnumField(
        ExperimentStatus, default=ExperimentStatus.DRAFT, index=True
    )
    version = fields.IntField(default=1)
    audience_fraction = fields.FloatField()
    targeting_rule = fields.TextField(null=True)
    owner = fields.ForeignKeyField(
        "models.UserModel",
        related_name="experiments",
        on_delete=OnDelete.RESTRICT,
    )
    completion = fields.JSONField(null=True)
    rollback_to_control_active = fields.BooleanField(default=False)
    target_metric = fields.ForeignKeyField(
        "models.MetricModel",
        to_field="key",
        null=True,
        on_delete=OnDelete.SET_NULL,
        related_name="target_metric_experiments",
    )
    metric_keys = fields.JSONField(default=list)
    variants: ReverseRelation["models.VariantModel"]  # type: ignore # noqa
    guardrail_configs: ReverseRelation["models.GuardrailConfigModel"]  # type: ignore # noqa
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "experiments"

    async def to_domain(self) -> Experiment:
        targeting_rule = None
        if self.targeting_rule and self.targeting_rule.strip():
            targeting_rule = TargetingRule(rule_expression=self.targeting_rule)

        approvals_models = await ApprovalModel.filter(
            experiment_id=self.id
        ).all()
        approvals = [a.to_domain() for a in approvals_models]

        completion = None
        if self.completion:
            completion = ExperimentCompletion(
                outcome=ExperimentOutcome(self.completion["outcome"]),
                winner_variant_id=self.completion.get("winner_variant_id"),
                comment=self.completion["comment"],
                completed_at=datetime.fromisoformat(
                    self.completion["completed_at"]
                ),
                completed_by=self.completion["completed_by"],
            )

        variants_list = await self.variants.all()
        variants = [variant.to_domain() for variant in variants_list]

        guardrail_list = await self.guardrail_configs.all()
        guardrails = [g.to_domain() for g in guardrail_list]

        return Experiment(
            id=self.id,
            flag_key=self.flag_key,
            variants=variants,
            owner_id=str(self.owner.id),
            name=self.name,
            status=self.status,
            version=self.version,
            audience_fraction=self.audience_fraction,
            targeting_rule=targeting_rule,
            approvals=approvals,
            guardrails=guardrails,
            completion=completion,
            rollback_to_control_active=self.rollback_to_control_active,
            target_metric_key=self.target_metric_id,  # type: ignore[arg-type]
            metric_keys=list(self.metric_keys or []),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, experiment: Experiment) -> ExperimentModel:
        completion_json = None
        if experiment.completion:
            completion_json = {
                "outcome": experiment.completion.outcome.value,
                "winner_variant_id": experiment.completion.winner_variant_id,
                "comment": experiment.completion.comment,
                "completed_at": experiment.completion.completed_at.isoformat(),
                "completed_by": str(experiment.completion.completed_by),
            }

        return cls(
            id=experiment.id,
            flag_key=experiment.flag_key,
            name=experiment.name,
            status=experiment.status,
            version=experiment.version,
            audience_fraction=experiment.audience_fraction,
            targeting_rule=experiment.targeting_rule.rule_expression
            if experiment.targeting_rule
            else None,
            owner_id=experiment.owner_id,
            completion=completion_json,
            rollback_to_control_active=experiment.rollback_to_control_active,
            target_metric_id=experiment.target_metric_key,
            metric_keys=list(experiment.metric_keys),
            created_at=experiment.created_at,
            updated_at=experiment.updated_at,
        )
