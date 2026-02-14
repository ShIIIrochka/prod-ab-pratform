from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class VariantModel(Model):
    """Tortoise модель для вариантов эксперимента.

    Соответствует domain.entities.variant.Variant
    """

    id = fields.IntField(pk=True, description="Auto-increment ID")
    experiment_id = fields.CharField(
        max_length=36, index=True, description="Experiment UUID"
    )
    name = fields.CharField(
        max_length=255, description="Variant name (unique in experiment)"
    )

    # Значение варианта (может быть str, int, float, bool)
    value_json = fields.JSONField(description="Variant value (any type)")

    weight = fields.FloatField(description="Traffic weight (0-1)")
    is_control = fields.BooleanField(description="Is control variant flag")

    class Meta:
        table = "variants"
        unique_together = [("experiment_id", "name")]
        indexes = [
            ("experiment_id",),
        ]
