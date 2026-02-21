from __future__ import annotations

from dataclasses import dataclass

from src.domain.value_objects.flag_value import FlagValueType


@dataclass
class FeatureFlag:
    key: str
    value_type: FlagValueType
    default_value: str | int | float | bool
    description: str | None = None

    def __post_init__(self) -> None:
        self._validate_value(self.default_value)

    def _validate_value(self, value) -> None:
        if self.value_type == FlagValueType.STRING and not isinstance(
            value, str
        ):
            msg = (
                f"Expected str for STRING type, got {value.__class__.__name__}"
            )
            raise ValueError(msg)
        if self.value_type == FlagValueType.NUMBER and (
            not isinstance(value, int | float) or type(value) is bool
        ):
            msg = f"Expected int/float for NUMBER type, got {value.__class__.__name__}"
            raise ValueError(msg)
        if self.value_type == FlagValueType.BOOL and not isinstance(
            value, bool
        ):
            msg = f"Expected bool for BOOL type, got {value.__class__.__name__}"
            raise ValueError(msg)

    def validate_variant_value(self, value: str | int | float | bool) -> None:
        self._validate_value(value)

    def update_default_value(self, new_value: str | int | float | bool) -> None:
        self._validate_value(new_value)
        self.default_value = new_value
