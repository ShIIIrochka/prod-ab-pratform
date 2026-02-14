from __future__ import annotations

from domain.exceptions.base import ApplicationException


class DecisionException(ApplicationException):
    """Базовое исключение для ошибок Decision API."""

    pass


class FeatureFlagNotFoundException(DecisionException):
    """Исключение когда feature flag не найден."""

    def __init__(self, flag_key: str):
        message = f"Feature flag not found: {flag_key}"
        details = {"flag_key": flag_key}
        super().__init__(message, details)


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
