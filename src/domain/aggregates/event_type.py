from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.aggregates import BaseEntity


@dataclass
class EventType(BaseEntity):
    key: str
    name: str
    description: str | None = None
    required_params: dict[str, Any] = field(default_factory=dict)
    requires_exposure: bool = False
