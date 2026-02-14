from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class FeatureFlagModel(Model):
    """Tortoise модель для feature flags.

    Соответствует domain.aggregates.feature_flag.FeatureFlag
    """

    key = fields.CharField(
        pk=True,
        max_length=255,
        description="Feature flag key (unique identifier)",
    )
    value_type = fields.CharField(
        max_length=50, description="FlagValueType enum: string, number, bool"
    )

    # FlagValue (value + value_type) хранится как JSON
    default_value_json = fields.JSONField(
        description="Default FlagValue as JSON: {value, value_type}"
    )

    description = fields.TextField(
        null=True, description="Human-readable description"
    )
    owner_id = fields.CharField(
        max_length=36, null=True, description="Owner User UUID"
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "feature_flags"
