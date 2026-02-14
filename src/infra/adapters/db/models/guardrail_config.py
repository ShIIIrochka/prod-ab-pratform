from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class GuardrailConfigModel(Model):
    """Tortoise модель для конфигурации guardrails.

    Соответствует domain.value_objects.guardrail_config.GuardrailConfig
    """

    id = fields.IntField(pk=True, description="Auto-increment ID")
    experiment_id = fields.CharField(
        max_length=36, index=True, description="Experiment UUID"
    )
    metric_key = fields.CharField(
        max_length=255, description="Metric key to monitor"
    )
    threshold = fields.FloatField(
        description="Threshold value for guardrail trigger"
    )
    observation_window_minutes = fields.IntField(
        description="Observation window in minutes"
    )
    action = fields.CharField(
        max_length=50,
        description="GuardrailAction enum: pause or rollback_to_control",
    )

    class Meta:
        table = "guardrail_configs"
        indexes = [
            ("experiment_id",),
        ]
