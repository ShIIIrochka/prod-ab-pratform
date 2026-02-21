from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class DecideRequest(BaseModel):
    subject_id: str = Field(..., min_length=1, description="Subject identifier")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Subject attributes for targeting",
    )
    flag_keys: list[str] = Field(
        ...,
        min_length=1,
        description="List of flag keys to resolve",
    )


class DecisionResponse(BaseModel):
    id: UUID
    subject_id: str
    flag_key: str
    value: str | int | float | bool
    experiment_id: UUID | None = None
    variant_id: UUID | None = None
    variant_name: str | None = None
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime, _info: Any) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp())

    class Config:
        from_attributes = True


class DecideResponse(BaseModel):
    decisions: dict[str, DecisionResponse]
