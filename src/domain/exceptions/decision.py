from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions.base import ApplicationException


class DecisionException(ApplicationException):
    """Базовое исключение для ошибок Decision API."""

    pass


@dataclass
class FeatureFlagNotFoundException(DecisionException):
    message = "Feature flag not found"


class ExperimentNotFoundException(DecisionException):
    """Исключение когда эксперимент не найден."""

    def __init__(
        self, experiment_id: str | None = None, flag_key: str | None = None
    ):
        message = "Experiment not found"
        details = {}
        if experiment_id:
            details["experiment_id"] = experiment_id
        if flag_key:
            details["flag_key"] = flag_key
        super().__init__(message, details)
