from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Approval:
    user_id: str
    comment: str | None
    timestamp: datetime
