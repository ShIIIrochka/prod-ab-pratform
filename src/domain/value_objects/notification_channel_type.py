from __future__ import annotations

from enum import StrEnum


class NotificationChannelType(StrEnum):
    SLACK = "slack"
    TELEGRAM = "telegram"
