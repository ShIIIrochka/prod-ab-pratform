from __future__ import annotations

import json

from datetime import datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from src.application.ports.pending_events_store import (
    PendingEventsStorePort,
)
from src.domain.aggregates.event import AttributionStatus, Event


# Префиксы ключей Redis
# pending:event:{event_id}     — JSON данных события (без TTL)
_PREFIX_EVENT = "pending:event:"
# pending:ttl:{event_id}       — маркер TTL (пустое значение, TTL 7 дней).
# Когда Redis удаляет этот ключ по истечении TTL, keyspace notification
# сигнализирует листенеру: пора перенести событие в БД как REJECTED.
PENDING_TTL_KEY_PREFIX = "pending:ttl:"
# pending:decision:{decision_id} — Set из event_id (индекс по decision)
_PREFIX_DECISION = "pending:decision:"


def _event_key(event_id: str) -> str:
    return f"{_PREFIX_EVENT}{event_id}"


def _ttl_marker_key(event_id: str) -> str:
    return f"{PENDING_TTL_KEY_PREFIX}{event_id}"


def _decision_key(decision_id: str) -> str:
    return f"{_PREFIX_DECISION}{decision_id}"


def _serialize_event(event: Event) -> str:
    """Сериализовать доменное событие в JSON."""
    return json.dumps(
        {
            "id": str(event.id),
            "event_type_key": event.event_type_key,
            "decision_id": event.decision_id,
            "subject_id": event.subject_id,
            "timestamp": event.timestamp.isoformat(),
            "props": event.props,
            "attribution_status": event.attribution_status.value,
        }
    )


def _deserialize_event(data: str | bytes) -> Event:
    """Десериализовать доменное событие из JSON."""
    payload: dict[str, Any] = json.loads(data)
    return Event(
        id=UUID(payload["id"]),
        event_type_key=payload["event_type_key"],
        decision_id=payload["decision_id"],
        subject_id=payload["subject_id"],
        timestamp=datetime.fromisoformat(payload["timestamp"]),
        props=payload["props"],
        attribution_status=AttributionStatus(payload["attribution_status"]),
    )


class RedisPendingEventsStore(PendingEventsStorePort):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def put(
        self,
        event: Event,
        ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        event_id = str(event.id)
        pipeline = self._redis.pipeline()

        # Данные события без TTL (читаем их при срабатывании expired notification)
        pipeline.set(_event_key(event_id), _serialize_event(event))

        # Маркер TTL — истекает через ttl_seconds, запускает keyspace notification
        pipeline.set(_ttl_marker_key(event_id), "", ex=ttl_seconds)

        # Индекс decision_id → set[event_id]
        pipeline.sadd(_decision_key(event.decision_id), event_id)
        pipeline.expire(_decision_key(event.decision_id), ttl_seconds)

        await pipeline.execute()

    async def exists(self, event_id: str) -> bool:
        return bool(await self._redis.exists(_event_key(str(event_id))))

    async def get_by_event_id(self, event_id: str) -> Event | None:
        data = await self._redis.get(_event_key(str(event_id)))
        if data is None:
            return None
        return _deserialize_event(data)

    async def get_by_decision_id(self, decision_id: str) -> list[Event]:
        event_ids: set[bytes] = await self._redis.smembers(
            _decision_key(decision_id)
        )
        if not event_ids:
            return []

        events: list[Event] = []
        for raw_id in event_ids:
            event_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            data = await self._redis.get(_event_key(event_id))
            if data is not None:
                events.append(_deserialize_event(data))
        return events

    async def delete_by_event_ids(self, event_ids: list[str]) -> None:
        if not event_ids:
            return

        # Читаем decision_id каждого события, чтобы убрать из индекса
        events_to_remove: list[Event] = []
        for event_id in event_ids:
            data = await self._redis.get(_event_key(str(event_id)))
            if data is not None:
                events_to_remove.append(_deserialize_event(data))

        pipeline = self._redis.pipeline()
        for event_id in event_ids:
            pipeline.delete(_event_key(str(event_id)))
            pipeline.delete(_ttl_marker_key(str(event_id)))

        for event in events_to_remove:
            pipeline.srem(_decision_key(event.decision_id), str(event.id))

        await pipeline.execute()
