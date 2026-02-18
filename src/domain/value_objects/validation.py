from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationFieldError:
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    success: bool
    errors: tuple[ValidationFieldError, ...] = field(default_factory=tuple)
    normalized_props: dict | None = None

    @classmethod
    def ok(cls, normalized_props: dict) -> ValidationResult:
        return cls(success=True, normalized_props=normalized_props)

    @classmethod
    def fail(cls, errors: list[ValidationFieldError]) -> ValidationResult:
        return cls(success=False, errors=tuple(errors))
