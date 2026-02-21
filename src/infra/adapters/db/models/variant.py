from __future__ import annotations

from uuid import UUID

from tortoise import fields
from tortoise.models import Model

from src.domain.entities.variant import Variant


class VariantModel(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)
    value = fields.JSONField()
    weight = fields.FloatField()
    is_control = fields.BooleanField()
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel", related_name="variants"
    )

    class Meta:
        table = "variants"
        unique_together = (("experiment", "name"),)

    def to_domain(self) -> Variant:
        return Variant(
            id=self.id,
            name=self.name,
            value=self.value.get("value"),
            weight=self.weight,
            is_control=self.is_control,
        )

    @classmethod
    def from_domain(cls, variant: Variant, experiment_id: UUID) -> VariantModel:
        return cls(
            id=variant.id,
            name=variant.name,
            value={"value": variant.value},
            weight=variant.weight,
            is_control=variant.is_control,
            experiment_id=experiment_id,
        )
