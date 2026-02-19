from __future__ import annotations

from uuid import UUID

from tortoise import fields
from tortoise.models import Model

from src.domain.value_objects.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)


class GuardrailConfigModel(Model):
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

    def to_domain(self) -> GuardrailConfig:
        return GuardrailConfig(
            metric_key=self.metric_key,
            threshold=self.threshold,
            observation_window_minutes=self.observation_window_minutes,
            action=GuardrailAction(self.action),
        )

    @classmethod
    def from_domain(
        cls, config: GuardrailConfig, experiment_id: UUID | str
    ) -> GuardrailConfigModel:
        return cls(
            experiment_id=str(experiment_id),
            metric_key=config.metric_key,
            threshold=config.threshold,
            observation_window_minutes=config.observation_window_minutes,
            action=config.action.value,
        )
