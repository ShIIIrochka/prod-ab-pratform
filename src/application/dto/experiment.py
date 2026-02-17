from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.value_objects.experiment_completion import ExperimentOutcome
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule


class VariantInput(BaseModel):
    name: str = Field(..., description="Variant name")
    value: str | int | float | bool = Field(..., description="Variant value")
    weight: float = Field(..., description="Variant weight")
    is_control: bool = Field(..., description="Is control variant")


class ExperimentCreateRequest(BaseModel):
    flag_key: str = Field(..., description="Feature flag key")
    name: str = Field(..., description="Experiment name")
    audience_fraction: float = Field(..., description="Audience fraction (0-1)")
    variants: list[VariantInput] = Field(..., description="Experiment variants")
    targeting_rule: str | None = Field(
        None, description="Optional targeting rule expression"
    )


class ExperimentUpdateRequest(BaseModel):
    name: str | None = Field(None, description="Experiment name")
    audience_fraction: float | None = Field(
        None, description="Audience fraction (0-1)"
    )
    variants: list[VariantInput] | None = Field(
        None, description="Experiment variants"
    )
    targeting_rule: str | None = Field(
        None, description="Optional targeting rule expression"
    )


class VariantResponse(BaseModel):
    id: UUID = Field(..., description="Variant ID")
    name: str = Field(..., description="Variant name")
    value: str | int | float | bool = Field(..., description="Variant value")
    weight: float = Field(..., description="Variant weight")
    is_control: bool = Field(..., description="Is control variant")

    class Config:
        from_attributes = True


class ExperimentResponse(BaseModel):
    id: UUID = Field(..., description="Experiment ID")
    flag_key: str = Field(..., description="Feature flag key")
    name: str = Field(..., description="Experiment name")
    status: ExperimentStatus = Field(..., description="Experiment status")
    version: int = Field(..., description="Experiment version")
    audience_fraction: float = Field(..., description="Audience fraction (0-1)")
    variants: list[VariantResponse] = Field(
        ..., description="Experiment variants"
    )
    targeting_rule: TargetingRule | None = Field(
        None, description="Optional targeting rule expression"
    )
    owner_id: str = Field(..., description="Owner user ID")

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentResponse] = Field(
        ..., description="List of experiments"
    )


class ApproveExperimentRequest(BaseModel):
    comment: str | None = Field(None, description="Optional approval comment")


class RequestChangesRequest(BaseModel):
    comment: str | None = Field(None, description="Optional comment")


class RejectExperimentRequest(BaseModel):
    comment: str | None = Field(None, description="Optional rejection comment")


class CompleteExperimentRequest(BaseModel):
    outcome: ExperimentOutcome = Field(..., description="Experiment outcome")
    comment: str = Field(..., description="Completion comment (required)")
    winner_variant_id: str | None = Field(
        None, description="Winner variant ID (required for ROLLOUT_WINNER)"
    )
