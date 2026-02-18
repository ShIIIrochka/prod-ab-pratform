from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventTypeCreateRequest(BaseModel):
    """Запрос на создание типа события."""

    key: str = Field(..., min_length=1, description="Event type key")
    name: str = Field(..., min_length=1, description="Human-readable name")
    description: str | None = Field(None, description="Event type description")
    required_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Required event parameters schema (e.g., {'screen': 'string'})",
    )
    requires_exposure: bool = Field(
        default=False,
        description="Whether event requires exposure for attribution",
    )


class EventTypeResponse(BaseModel):
    """Ответ с типом события."""

    key: str
    name: str
    description: str | None
    required_params: dict[str, Any]
    requires_exposure: bool

    class Config:
        from_attributes = True


class EventTypeListResponse(BaseModel):
    """Список типов событий."""

    event_types: list[EventTypeResponse]
