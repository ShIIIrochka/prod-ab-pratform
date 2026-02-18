from __future__ import annotations

import hashlib
import json

from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.ports.event_id_generator import EventIdGeneratorPort


class EventIdGenerator(EventIdGeneratorPort):
    def generate(
        self,
        event_type_key: str,
        decision_id: str,
        subject_id: str,
        timestamp: datetime,
        props: dict[str, Any],
    ) -> UUID:
        # Сортируем props для детерминизма
        sorted_props = json.dumps(props, sort_keys=True)
        timestamp_str = timestamp.isoformat()

        seed_parts = [
            event_type_key,
            decision_id,
            subject_id,
            timestamp_str,
            sorted_props,
        ]
        seed = ":".join(seed_parts)
        h = hashlib.sha256(seed.encode()).digest()

        # Детерминированный UUID из хеша (как у decision_id)
        return UUID(bytes=h[:16], version=4)
