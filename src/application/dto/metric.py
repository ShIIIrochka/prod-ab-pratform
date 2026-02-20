from __future__ import annotations

from pydantic import BaseModel, Field


class MetricCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, description="Unique metric key")
    name: str = Field(
        ..., min_length=1, description="Human-readable metric name"
    )
    calculation_rule: str = Field(
        ...,
        description=(
            "Calculation rule in JSON or DSL format. Examples: "
            '{"type":"COUNT","event_type_key":"conversion"}, '
            '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"conversion"},'
            '"denominator":{"type":"COUNT","event_type_key":"exposure"}}, '
            "COUNT(conversion), "
            "COUNT(error) / COUNT(exposure), "
            "AVG(latency, duration_ms), "
            "P95(latency, duration_ms)"
        ),
    )
    aggregation_unit: str = Field(
        "event",
        description="Aggregation unit: 'event' (count events) or 'user' (count unique users)",
    )
    description: str | None = Field(None, description="Metric description")


class MetricResponse(BaseModel):
    key: str = Field(..., description="Metric key (primary identifier)")
    name: str
    calculation_rule: str
    aggregation_unit: str
    description: str | None

    class Config:
        from_attributes = True


class MetricListResponse(BaseModel):
    metrics: list[MetricResponse]
