from __future__ import annotations

from uuid import UUID

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.entities.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)


class GuardrailConfigModel(Model):
    id = fields.UUIDField(pk=True, generate=True)
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel",
        related_name="guardrail_configs",
        on_delete=OnDelete.CASCADE,
    )
    metric = fields.ForeignKeyField(
        "models.MetricModel",
        to_field="key",
        related_name="guardrail_configs",
        on_delete=OnDelete.RESTRICT,
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
            ("metric_id",),
        ]

    def to_domain(self) -> GuardrailConfig:
        return GuardrailConfig(
            id=self.id,
            metric_key=self.metric_id,  # type: ignore[arg-type]
            threshold=self.threshold,
            observation_window_minutes=self.observation_window_minutes,
            action=GuardrailAction(self.action),
        )

    @classmethod
    def from_domain(
        cls, config: GuardrailConfig, experiment_id: UUID
    ) -> GuardrailConfigModel:
        return cls(
            experiment_id=experiment_id,
            metric_id=config.metric_key,
            threshold=config.threshold,
            observation_window_minutes=config.observation_window_minutes,
            action=config.action.value,
        )
