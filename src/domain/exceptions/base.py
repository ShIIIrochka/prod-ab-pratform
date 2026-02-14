from __future__ import annotations


class ApplicationException(Exception):
    """Базовое исключение для всех доменных ошибок приложения."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message
