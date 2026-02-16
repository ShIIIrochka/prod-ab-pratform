from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DecideRequest(BaseModel):
    subject_id: str = Field(..., min_length=1, description="Subject identifier")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Subject attributes for targeting",
    )
    flag_key: str = Field(
        ...,
        min_length=1,
        description="Flag key to resolve",
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

    class Config:
        from_attributes = True


class DecideResponse(BaseModel):
    decision: DecisionResponse
