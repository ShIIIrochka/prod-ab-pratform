from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID


class EventIdGeneratorPort(ABC):
    @abstractmethod
    def generate(
        self,
        event_type_key: str,
        decision_id: str,
        subject_id: str,
        timestamp: datetime,
        props: dict[str, Any],
    ) -> UUID:
        raise NotImplementedError
