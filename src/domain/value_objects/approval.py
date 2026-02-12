from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Approval:
    user_id: UUID
    comment: str | None
    timestamp: datetime
