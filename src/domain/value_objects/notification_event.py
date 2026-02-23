from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


def make_notification_event_id(
    event_type: str, entity_id: UUID, version: int
) -> UUID:
    namespace = uuid.UUID("b3a9e2c1-7f4d-4e8a-a1b2-3c4d5e6f7890")
    key = f"{event_type}:{entity_id}:{version}"
    return uuid.uuid5(namespace, key)


@dataclass(frozen=True)
class NotificationEvent:
    event_id: UUID
    event_type: str
    entity_type: str
    entity_id: UUID
    payload: dict
    occurred_at: datetime = field(default_factory=datetime.utcnow)
