from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.flag_value import FlagValue, FlagValueType


@dataclass
class FeatureFlag:
    key: str
    value_type: FlagValueType
    default_value: FlagValue
    description: str | None = None
    owner_id: str | None = None

    def __post_init__(self) -> None:
        if self.default_value.value_type != self.value_type:
            msg = (
                f"Default value type {self.default_value.value_type} "
                f"does not match flag value type {self.value_type}"
            )
            raise ValueError(msg)

    def update_default_value(self, new_value: FlagValue) -> None:
        if new_value.value_type != self.value_type:
            msg = (
                f"Cannot update default value: type mismatch. "
                f"Expected {self.value_type}, got {new_value.value_type}"
            )
            raise ValueError(msg)
        self.default_value = new_value
