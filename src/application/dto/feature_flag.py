from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.value_objects.flag_value import FlagValueType


class FeatureFlagCreateRequest(BaseModel):
    key: str = Field(..., description="Feature flag key")
    value_type: FlagValueType = Field(..., description="Value type")
    default_value: str | int | float | bool = Field(
        ..., description="Default value"
    )
    description: str | None = Field(None, description="Optional description")


class FeatureFlagResponse(BaseModel):
    key: str = Field(..., description="Feature flag key")
    value_type: FlagValueType = Field(..., description="Value type")
    default_value: str | int | float | bool = Field(
        ..., description="Default value"
    )
    description: str | None = Field(None, description="Optional description")

    class Config:
        from_attributes = True


class FeatureFlagListResponse(BaseModel):
    flags: list[FeatureFlagResponse] = Field(
        ..., description="List of feature flags"
    )


class FeatureFlagUpdateDefaultRequest(BaseModel):
    default_value: str | int | float | bool = Field(
        ..., description="New default value"
    )
