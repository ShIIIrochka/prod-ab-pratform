from __future__ import annotations

from enum import StrEnum


class NotificationDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    PERMANENT_FAILED = "permanent_failed"
    SKIPPED_RATE_LIMITED = "skipped_rate_limited"
