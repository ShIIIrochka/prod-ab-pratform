from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FlagValueType(StrEnum):
    """Тип значения feature flag."""

    STRING = "string"
    NUMBER = "number"
    BOOL = "bool"
