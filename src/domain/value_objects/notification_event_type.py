from __future__ import annotations

from enum import StrEnum


class NotificationEventType(StrEnum):
    EXPERIMENT_SENT_TO_REVIEW = "experiment.sent_to_review"
    EXPERIMENT_APPROVED = "experiment.approved"
    EXPERIMENT_CHANGES_REQUESTED = "experiment.changes_requested"
    EXPERIMENT_REJECTED = "experiment.rejected"
    EXPERIMENT_LAUNCHED = "experiment.launched"
    EXPERIMENT_PAUSED = "experiment.paused"
    EXPERIMENT_COMPLETED = "experiment.completed"
    EXPERIMENT_ARCHIVED = "experiment.archived"
    GUARDRAIL_TRIGGERED = "guardrail.triggered"
