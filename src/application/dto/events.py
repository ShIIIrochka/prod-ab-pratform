from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SendEventRequest(BaseModel):
    event_type_key: str = Field(..., min_length=1, description="Event type key")
    decision_id: UUID = Field(..., description="Decision ID for attribution")
    timestamp: datetime = Field(
        ..., description="Event timestamp — unix seconds (UTC)"
    )
    props: dict[str, Any] = Field(
        default_factory=dict, description="Event properties"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, int | float):
            return datetime.fromtimestamp(v, tz=UTC)
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=UTC)
            return v
        raise ValueError(f"Cannot parse timestamp: {v!r}")


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
