from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from domain.aggregates import FeatureFlag
from domain.value_objects import FlagValueType


class FeatureFlagModel(Model):
    key = fields.CharField(
        pk=True,
        max_length=255,
    )
    value_type = fields.CharEnumField(FlagValueType, default=FlagValueType.STRING)
    default_value = fields.JSONField()
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "feature_flags"

    def to_domain(self) -> FeatureFlag:
        return FeatureFlag(
            key=self.key,
            value_type=self.value_type,
            default_value=self.default_value,
            description=self.description,
        )

    @classmethod
    def from_domain(cls, feature_flag: FeatureFlag) -> FeatureFlagModel:
        return cls(
            key=feature_flag.key,
            value_type=feature_flag.value_type,
            default_value=feature_flag.default_value,
            description=feature_flag.description,
        )