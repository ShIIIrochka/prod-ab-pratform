from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ExperimentEventType(StrEnum):
    SENT_TO_REVIEW = "sent_to_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    LAUNCHED = "launched"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ExperimentStatusChanged:
    event_type: ExperimentEventType
    experiment_id: UUID
    experiment_name: str
    flag_key: str
    owner_id: str
    status: str
    version: int
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GuardrailTriggered:
    experiment_id: UUID
    experiment_name: str
    flag_key: str
    owner_id: str
    metric_key: str
    threshold: float
    actual_value: float
    action: str
    triggered_at: datetime
    version: int
