from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.value_objects.validation import ValidationResult


class EventValidatorPort(ABC):
    @abstractmethod
    def validate(
        self,
        required_params: dict[str, Any],
        props: dict[str, Any],
    ) -> ValidationResult:
        raise NotImplementedError
