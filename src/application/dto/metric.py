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
            "JSON calculation rule. Examples: "
            '{"type":"COUNT","event_type_key":"conversion"}, '
            '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"conversion"},'
            '"denominator":{"type":"COUNT","event_type_key":"exposure"}}, '
            '{"type":"PERCENTILE","event_type_key":"latency","property":"duration_ms","percentile":95}'
        ),
    )
    requires_exposure: bool = Field(
        False,
        description="Whether metric requires exposure attribution",
    )
    description: str | None = Field(None, description="Metric description")


class MetricResponse(BaseModel):
    key: str
    name: str
    calculation_rule: str
    requires_exposure: bool
    description: str | None

    class Config:
        from_attributes = True


class MetricListResponse(BaseModel):
    metrics: list[MetricResponse]
