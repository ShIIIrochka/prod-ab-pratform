from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.value_objects.guardrail_config import GuardrailAction
from src.domain.value_objects.guardrail_trigger import GuardrailTrigger


class GuardrailTriggerModel(Model):
    id = fields.UUIDField(pk=True, generate=True)
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel",
        related_name="guardrail_triggers",
        on_delete=OnDelete.CASCADE,
    )
    metric = fields.ForeignKeyField(
        "models.MetricModel",
        to_field="key",
        related_name="guardrail_triggers",
        on_delete=OnDelete.SET_NULL,
        null=True,
    )
    threshold = fields.FloatField(description="Threshold value")
    observation_window_minutes = fields.IntField(
        description="Observation window in minutes"
    )
    action = fields.CharField(
        max_length=50,
        description="GuardrailAction enum: pause or rollback_to_control",
    )
    actual_value = fields.FloatField(
        description="Actual metric value at the time of trigger"
    )
    triggered_at = fields.DatetimeField(
        auto_now_add=True, description="Timestamp when guardrail was triggered"
    )

    class Meta:
        table = "guardrail_triggers"
        indexes = [
            ("experiment_id",),
            ("triggered_at",),
            ("metric_id",),
        ]

    def to_domain(self) -> GuardrailTrigger:
        return GuardrailTrigger(
            id=self.id,
            experiment_id=self.experiment_id,  # type: ignore[arg-type]
            metric_key=self.metric_id or "",  # type: ignore[arg-type]
            threshold=self.threshold,
            observation_window_minutes=self.observation_window_minutes,
            action=GuardrailAction(self.action),
            actual_value=self.actual_value,
            triggered_at=self.triggered_at,
        )

    @classmethod
    def from_domain(cls, trigger: GuardrailTrigger) -> GuardrailTriggerModel:
        return cls(
            experiment_id=trigger.experiment_id,
            metric_id=trigger.metric_key if trigger.metric_key else None,
            threshold=trigger.threshold,
            observation_window_minutes=trigger.observation_window_minutes,
            action=trigger.action.value,
            actual_value=trigger.actual_value,
            triggered_at=trigger.triggered_at,
        )
