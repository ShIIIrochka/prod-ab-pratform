from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class VariantModel(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    value = fields.JSONField()
    weight = fields.FloatField()
    is_control = fields.BooleanField()
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel", related_name="variants"
    )

    class Meta:
        table = "variants"
