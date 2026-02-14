from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class DecisionModel(Model):
    id = fields.CharField(
        pk=True, max_length=36, description="Decision ID (UUID, deterministic)"
    )
    subject_id = fields.CharField(
        max_length=255, index=True, description="Subject ID"
    )
    flag_key = fields.CharField(
        max_length=255, index=True, description="Flag key"
    )
    value = fields.JSONField(description="Decision value")
    experiment_id = fields.CharField(
        max_length=36,
        null=True,
        index=True,
        description="Experiment ID if applied",
    )
    variant_id = fields.CharField(
        max_length=255, null=True, description="Variant ID if applied"
    )
    experiment_version = fields.IntField(
        null=True, description="Experiment version at decision time"
    )
    timestamp = fields.DatetimeField(description="Decision timestamp")

    class Meta:
        table = "decisions"
        indexes = [
            ("subject_id", "flag_key"),
        ]
