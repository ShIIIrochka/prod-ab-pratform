from __future__ import annotations

from enum import StrEnum


class ExperimentStatus(StrEnum):
    DRAFT = "draft"  # Черновик
    ON_REVIEW = "on_review"  # На ревью
    APPROVED = "approved"  # Одобрен
    RUNNING = "running"  # Запущен
    PAUSED = "paused"  # На паузе
    COMPLETED = "completed"  # Завершён
    ARCHIVED = "archived"  # В архиве
    REJECTED = "rejected"  # Отклонён

    def is_active(self) -> bool:
        return self in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED)

    def can_be_edited(self) -> bool:
        return self == ExperimentStatus.DRAFT

    def can_be_launched(self) -> bool:
        return self in (ExperimentStatus.APPROVED, ExperimentStatus.PAUSED)
