from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.aggregates.decision import Decision


class DecisionModel(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.UserModel",
        related_name="decisions",
        on_delete=OnDelete.RESTRICT,
    )
    flag_key = fields.CharField(max_length=255, index=True)
    value = fields.JSONField()
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel",
        related_name="decisions",
        on_delete=OnDelete.SET_NULL,
        null=True,
    )
    variant = fields.OneToOneField(
        "models.VariantModel",
        related_name="decision",
        on_delete=OnDelete.CASCADE,
        null=True,
    )
    experiment_version = fields.IntField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "decisions"

    def to_domain(self) -> Decision:
        return Decision(
            id=self.id,
            subject_id=self.user_id,
            flag_key=self.flag_key,
            value=self.value.get("value"),
            experiment_id=self.experiment.id if self.experiment else None,
            variant_id=self.variant.id if self.variant else None,
            experiment_version=self.experiment_version,
            timestamp=self.timestamp,
        )

    @classmethod
    def from_domain(cls, decision: Decision) -> DecisionModel:
        return cls(
            id=decision.id,
            user_id=decision.subject_id,
            flag_key=decision.flag_key,
            value={"value": decision.value},
            experiment_id=decision.experiment_id,
            variant_id=decision.variant_id,
            experiment_version=decision.experiment_version,
            timestamp=decision.timestamp,
        )
