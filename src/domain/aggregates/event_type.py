"""Агрегат EventType - каталог типов событий."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventType:
    """Тип события в каталоге.

    Агрегат-корень для управления типами событий.
    """

    key: str
    name: str
    description: str | None = None
    required_params: dict[str, Any] = field(default_factory=dict)
    requires_exposure: bool = False

    def __post_init__(self) -> None:
        """Валидация типа события."""
        if not self.key:
            msg = "Event type key cannot be empty"
            raise ValueError(msg)
        if not self.name:
            msg = "Event type name cannot be empty"
            raise ValueError(msg)
