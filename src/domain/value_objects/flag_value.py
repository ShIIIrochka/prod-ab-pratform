from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FlagValueType(StrEnum):
    """Тип значения feature flag."""

    STRING = "string"
    NUMBER = "number"
    BOOL = "bool"


@dataclass(frozen=True)
class FlagValue:
    value: str | int | float | bool
    value_type: FlagValueType

    def __post_init__(self) -> None:
        if self.value_type == FlagValueType.STRING and not isinstance(
            self.value, str
        ):
            msg = f"Expected str for STRING type, got {type(self.value)}"
            raise ValueError(msg)
        if self.value_type == FlagValueType.NUMBER and not isinstance(
            self.value, int | float
        ):
            msg = f"Expected int/float for NUMBER type, got {type(self.value)}"
            raise ValueError(msg)
        if self.value_type == FlagValueType.BOOL and not isinstance(
            self.value, bool
        ):
            msg = f"Expected bool for BOOL type, got {type(self.value)}"
            raise ValueError(msg)
