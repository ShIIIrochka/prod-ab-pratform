from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.value_objects.experiment_completion import ExperimentOutcome
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.guardrail_config import GuardrailAction
from src.domain.value_objects.targeting_rule import TargetingRule


class VariantInput(BaseModel):
    name: str = Field(..., description="Variant name")
    value: str | int | float | bool = Field(..., description="Variant value")
    weight: float = Field(..., description="Variant weight")
    is_control: bool = Field(..., description="Is control variant")


class GuardrailConfigInput(BaseModel):
    metric_key: str = Field(..., description="Metric key to monitor")
    threshold: float = Field(
        ..., description="Threshold value for guardrail trigger"
    )
    observation_window_minutes: int = Field(
        ..., gt=0, description="Observation window in minutes"
    )
    action: GuardrailAction = Field(
        ..., description="Action on trigger: pause or rollback_to_control"
    )


class GuardrailConfigResponse(BaseModel):
    metric_key: str
    threshold: float
    observation_window_minutes: int
    action: GuardrailAction

    class Config:
        from_attributes = True


class ExperimentCreateRequest(BaseModel):
    flag_key: str = Field(..., description="Feature flag key")
    name: str = Field(..., description="Experiment name")
    audience_fraction: float = Field(..., description="Audience fraction (0-1)")
    variants: list[VariantInput] = Field(..., description="Experiment variants")
    targeting_rule: str | None = Field(
        None, description="Optional targeting rule expression"
    )
    target_metric_key: str | None = Field(
        None, description="Primary metric key for the experiment"
    )
    metric_keys: list[str] = Field(
        default_factory=list,
        description="Additional metric keys to track",
    )
    guardrails: list[GuardrailConfigInput] = Field(
        default_factory=list,
        description="Guardrail rules for automatic experiment stopping",
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
    target_metric_key: str | None = Field(
        None, description="Primary metric key"
    )
    metric_keys: list[str] | None = Field(
        None, description="Additional metric keys to track"
    )
    guardrails: list[GuardrailConfigInput] | None = Field(
        None,
        description="Guardrail rules (replaces all existing guardrails)",
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
    target_metric_key: str | None = Field(
        None, description="Primary metric key"
    )
    metric_keys: list[str] = Field(
        default_factory=list, description="Additional metric keys"
    )
    guardrails: list[GuardrailConfigResponse] = Field(
        default_factory=list,
        description="Guardrail rules for this experiment",
    )

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
