from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class ExperimentModel(Model):
    """Tortoise модель для экспериментов.

    Соответствует domain.aggregates.experiment.Experiment
    """

    id = fields.CharField(pk=True, max_length=36, description="Experiment UUID")
    flag_key = fields.CharField(
        max_length=255, index=True, description="Feature flag key"
    )
    name = fields.CharField(max_length=500, description="Experiment name")
    status = fields.CharField(
        max_length=50, index=True, description="ExperimentStatus enum value"
    )
    version = fields.IntField(default=1, description="Configuration version")
    audience_fraction = fields.FloatField(
        description="Fraction of audience in experiment (0-1)"
    )

    # TargetingRule хранится как JSON (rule_expression)
    targeting_rule_json = fields.JSONField(
        null=True, description="TargetingRule as JSON"
    )

    owner_id = fields.CharField(max_length=36, description="Owner User UUID")

    # Метрики
    target_metric_key = fields.CharField(
        max_length=255, null=True, description="Primary metric key"
    )
    metric_keys_json = fields.JSONField(
        default=list, description="List of metric keys"
    )

    # Состояние
    rollback_to_control_active = fields.BooleanField(
        default=False, description="Rollback to control mode active"
    )

    # ExperimentCompletion хранится как JSON (outcome, winner_variant_id, comment, etc)
    completion_json = fields.JSONField(
        null=True, description="ExperimentCompletion as JSON"
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "experiments"
        indexes = [
            ("flag_key", "status"),  # Критично для get_active_by_flag_key
        ]
