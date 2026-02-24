from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class MetricValueResponse(BaseModel):
    metric_key: str = Field(..., description="Metric key")
    metric_name: str = Field(..., description="Metric human-readable name")
    value: float = Field(..., description="Calculated metric value")
    is_primary: bool = Field(
        False, description="Whether this is the primary target metric"
    )
    aggregation_unit: str = Field(
        "event",
        description="Aggregation unit used for this metric: 'event' or 'user'",
    )


class MetricDynamicsPoint(BaseModel):
    timestamp: int = Field(
        ...,
        description="Start of the time bucket (daily granularity), unix seconds UTC",
    )
    value: float = Field(..., description="Metric value for this time bucket")


class MetricDynamics(BaseModel):
    metric_key: str
    points: list[MetricDynamicsPoint]


class VariantReportResponse(BaseModel):
    variant_name: str = Field(..., description="Variant name")
    is_control: bool = Field(
        False, description="Whether this is the control variant"
    )
    metrics: list[MetricValueResponse] = Field(
        default_factory=list, description="Metric values for this variant"
    )
    dynamics: list[MetricDynamics] = Field(
        default_factory=list,
        description="Daily dynamics for each metric in this variant (only days with data)",
    )


class OverallReportResponse(BaseModel):
    """Aggregated metrics across all variants combined (calculated on the full event set)."""

    metrics: list[MetricValueResponse] = Field(
        default_factory=list,
        description="Metric values across all experiment events",
    )
    dynamics: list[MetricDynamics] = Field(
        default_factory=list,
        description="Daily dynamics for each metric across all experiment events",
    )


class DataQualitySummary(BaseModel):
    """Summary for Experiment Insights UI: traffic distribution and attributed counts."""

    variant_event_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Number of attributed events per variant name (for traffic balance)",
    )
    total_attributed_events: int = Field(
        0,
        description="Total attributed events in the report window",
    )


class ExperimentReportResponse(BaseModel):
    experiment_id: UUID
    experiment_name: str
    # Unix seconds (UTC)
    from_time: int = Field(
        ..., description="Report window start (inclusive), unix seconds UTC"
    )
    to_time: int = Field(
        ..., description="Report window end (exclusive), unix seconds UTC"
    )
    overall: OverallReportResponse = Field(
        default_factory=OverallReportResponse,
        description="Metrics aggregated across all variants combined",
    )
    variants: list[VariantReportResponse] = Field(
        default_factory=list,
        description="Per-variant metric reports",
    )
    data_quality: DataQualitySummary | None = Field(
        default=None,
        description="Quality summary for Insights UI: variant counts, total attributed",
    )
    context: dict = Field(
        default_factory=dict,
        description="Report context: window, attribution, aggregation unit",
    )
