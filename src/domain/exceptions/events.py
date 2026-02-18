from __future__ import annotations


class EventTypeNotFoundError(Exception):
    """Тип события не найден."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Event type not found: {key}")


class InvalidEventError(Exception):
    """Невалидное событие."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DecisionNotFoundError(Exception):
    """Decision ID не найден."""

    def __init__(self, decision_id: str) -> None:
        self.decision_id = decision_id
        super().__init__(f"Decision not found: {decision_id}")


class ExposureRequiredError(Exception):
    """Требуется exposure событие для атрибуции."""

    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Exposure required for event: {event_id}")
