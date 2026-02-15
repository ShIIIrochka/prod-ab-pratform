from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete, ReverseRelation
from tortoise.models import Model

from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule


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
    # target_metric_key = fields.CharField(
    #     max_length=255, null=True
    # )
    # metric_keys_json = fields.JSONField(
    #     default=list, description="List of metric keys"
    # )
    # rollback_to_control_active = fields.BooleanField(default=False)
    # completion_json = fields.JSONField(
    #     null=True, description="ExperimentCompletion as JSON"
    # )
    variants: ReverseRelation["models.VariantModel"]  # type: ignore # noqa
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "experiments"

    def to_domain(self) -> Experiment:
        return Experiment(
            id=self.id,
            flag_key=self.flag_key,
            variants=[variant.to_domain() for variant in self.variants],
            owner_id=self.owner.id,
            name=self.name,
            status=self.status,
            version=self.version,
            audience_fraction=self.audience_fraction,
            targeting_rule=TargetingRule(rule_expression=self.targeting_rule),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
