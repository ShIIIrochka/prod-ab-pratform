from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetricValueResponse(BaseModel):
    metric_key: str = Field(..., description="Metric key")
    metric_name: str = Field(..., description="Metric human-readable name")
    value: float = Field(..., description="Calculated metric value")
    is_primary: bool = Field(
        False, description="Whether this is the primary target metric"
    )


class MetricDynamicsPoint(BaseModel):
    timestamp: datetime = Field(
        ..., description="Start of the time bucket (daily granularity)"
    )
    value: float = Field(..., description="Metric value for this time bucket")


class MetricDynamics(BaseModel):
    metric_key: str
    points: list[MetricDynamicsPoint]


class VariantReportResponse(BaseModel):
    variant_name: str = Field(..., description="Variant name")
    metrics: list[MetricValueResponse] = Field(
        default_factory=list, description="Metric values for this variant"
    )
    dynamics: list[MetricDynamics] = Field(
        default_factory=list,
        description="Daily dynamics for each metric in this variant",
    )


class ExperimentReportResponse(BaseModel):
    experiment_id: UUID
    experiment_name: str
    from_time: datetime = Field(
        ..., description="Report window start (inclusive)"
    )
    to_time: datetime = Field(..., description="Report window end (exclusive)")
    variants: list[VariantReportResponse] = Field(
        default_factory=list,
        description="Per-variant metric reports",
    )
    context: dict = Field(
        default_factory=dict,
        description="Report context: window, attribution, aggregation unit",
    )
