from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from domain.value_objects import ExperimentStatus
from infra.adapters.db.models import UserModel


class ExperimentModel(Model):
    id = fields.UUIDField(pk=True)
    flag_key = fields.CharField(max_length=255, index=True)
    name = fields.CharField(max_length=255)
    status = fields.CharEnumField(ExperimentStatus, defalt=ExperimentStatus.DRAFT, index=True)
    version = fields.IntField(default=1)
    audience_fraction = fields.FloatField()
    targeting_rule = fields.TextField(null=True)
    owner = fields.ForeignKeyField(
        UserModel,
        related_name="experiments",
        on_delete=OnDelete.RESTRICT,
    )
    target_metric_key = fields.CharField(
        max_length=255, null=True
    )
    metric_keys_json = fields.JSONField(
        default=list, description="List of metric keys"
    )
    rollback_to_control_active = fields.BooleanField(
        default=False, description="Rollback to control mode active"
    )
    completion_json = fields.JSONField(
        null=True, description="ExperimentCompletion as JSON"
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "experiments"
