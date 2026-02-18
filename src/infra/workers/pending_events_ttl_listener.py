from __future__ import annotations

import asyncio
import logging

from redis.asyncio import Redis

from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.pending_events_store import PendingEventsStorePort
from src.infra.adapters.services.pending_events_store import (
    RedisPendingEventsStore,
)


logger = logging.getLogger(__name__)


class PendingEventsTTLListener:
    _EXPIRED_CHANNEL_PATTERN = "__keyevent@*__:expired"

    def __init__(
        self,
        redis: Redis,
        pending_store: PendingEventsStorePort,
        events_repository: EventsRepositoryPort,
    ) -> None:
        self._redis = redis
        self._pending_store = pending_store
        self._events_repository = events_repository
        self._ttl_prefix = RedisPendingEventsStore.PENDING_TTL_KEY_PREFIX

    async def start(self) -> None:
        await self._redis.config_set("notify-keyspace-events", "Ex")
        logger.info("[Redis] Keyspace notifications enabled (Ex)")

        pubsub = self._redis.pubsub()
        await pubsub.psubscribe(self._EXPIRED_CHANNEL_PATTERN)
        logger.info(
            f"[Redis] Subscribed to '{self._EXPIRED_CHANNEL_PATTERN}', "
            "listening for expired pending events"
        )

        try:
            async for message in pubsub.listen():
                if message is None or message["type"] != "pmessage":
                    continue

                expired_key: str = message["data"]
                if not expired_key.startswith(self._ttl_prefix):
                    continue

                event_id = expired_key[len(self._ttl_prefix) :]
                logger.debug(
                    f"[Redis] TTL expired for pending event {event_id}"
                )

                try:
                    await self._handle_expired(event_id)
                except Exception:
                    logger.exception(
                        f"[Redis] Failed to handle expired pending event {event_id}"
                    )

        except asyncio.CancelledError:
            await pubsub.punsubscribe(self._EXPIRED_CHANNEL_PATTERN)
            await pubsub.aclose()
            logger.info("[Redis] TTL listener stopped")
            raise

    async def _handle_expired(self, event_id: str) -> None:
        """Перенести просроченное pending-событие в БД как REJECTED."""
        event = await self._pending_store.get_by_event_id(event_id)
        if event is None:
            # Уже обработано — exposure успел прийти раньше истечения TTL
            logger.debug(
                f"[Redis] Pending event {event_id} already removed, skip"
            )
            return

        event.mark_as_rejected()
        await self._events_repository.save(event)
        await self._pending_store.delete_by_event_ids([event_id])

        logger.info(f"[Redis] Pending event {event_id} moved to DB as REJECTED")
