from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SendEventRequest(BaseModel):
    event_type_key: str = Field(..., min_length=1, description="Event type key")
    decision_id: str = Field(
        ..., min_length=1, description="Decision ID for attribution"
    )
    timestamp: datetime = Field(..., description="Event timestamp")
    props: dict[str, Any] = Field(
        default_factory=dict, description="Event properties"
    )


class SendEventsRequest(BaseModel):
    # Убираем типизацию чтоб пайдентик не райзил 422
    events: list[Any] = Field(
        ..., min_length=1, max_length=500, description="List of events to send"
    )


class EventErrorDetail(BaseModel):
    index: int = Field(..., description="Index of the event in the request")
    event_type_key: str = Field(..., description="Event type key")
    reason: str = Field(..., description="Error reason")


class SendEventsResponse(BaseModel):
    accepted: int = Field(..., description="Number of accepted events")
    duplicates: int = Field(..., description="Number of duplicate events")
    rejected: int = Field(..., description="Number of rejected events")
    errors: list[EventErrorDetail] = Field(
        default_factory=list, description="Details of rejected events"
    )
