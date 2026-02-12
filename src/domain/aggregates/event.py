from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class AttributionStatus(StrEnum):
    PENDING = "pending"  # Ожидает exposure события
    ATTRIBUTED = "attributed"  # Атрибутировано к решению
    REJECTED = "rejected"  # Отклонено (нет exposure или истекло окно)


@dataclass
class Event:
    id: str
    event_type_key: str
    decision_id: str
    subject_id: str
    timestamp: datetime
    props: dict[str, Any]
    attribution_status: AttributionStatus = AttributionStatus.PENDING

    def mark_as_attributed(self) -> None:
        self.attribution_status = AttributionStatus.ATTRIBUTED

    def mark_as_rejected(self) -> None:
        self.attribution_status = AttributionStatus.REJECTED
