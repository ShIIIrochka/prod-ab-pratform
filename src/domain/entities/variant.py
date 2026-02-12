from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Variant:
    name: str
    value: str | int | float | bool
    weight: float
    is_control: bool

    def __post_init__(self) -> None:
        if self.weight < 0 or self.weight > 1:
            msg = f"Weight must be between 0 and 1, got {self.weight}"
            raise ValueError(msg)

    def __eq__(self, other):
        if not isinstance(other, Variant):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)
