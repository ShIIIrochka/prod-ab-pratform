from __future__ import annotations

from datetime import datetime
from typing import Any

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
    decision_id: str
    subject_id: str
    flag_key: str
    value: str | int | float | bool
    experiment_id: str | None = None
    variant_id: str | None = None
    timestamp: datetime


class DecideResponse(BaseModel):
    """Ответ Decision API с одним решением (MVP: 1 флаг → 1 решение)."""

    decision: DecisionResponse
