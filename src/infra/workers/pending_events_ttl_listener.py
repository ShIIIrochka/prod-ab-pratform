from __future__ import annotations

import asyncio
import logging

from redis.asyncio import Redis

from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.pending_events_store import PendingEventsStorePort
from src.infra.adapters.services.pending_events_store import (
    PENDING_TTL_KEY_PREFIX,
)


logger = logging.getLogger(__name__)

_EXPIRED_CHANNEL_PATTERN = "__keyevent@*__:expired"


async def listen_for_expired_pending_events(
    redis: Redis,
    pending_store: PendingEventsStorePort,
    events_repository: EventsRepositoryPort,
) -> None:
    await redis.config_set("notify-keyspace-events", "Ex")
    logger.info("[Redis] Keyspace notifications enabled (Ex)")

    pubsub = redis.pubsub()
    await pubsub.psubscribe(_EXPIRED_CHANNEL_PATTERN)
    logger.info(
        f"[Redis] Subscribed to '{_EXPIRED_CHANNEL_PATTERN}', "
        "listening for expired pending events"
    )

    try:
        async for message in pubsub.listen():
            if message is None or message["type"] != "pmessage":
                continue

            expired_key = message["data"]
            if isinstance(expired_key, bytes):
                expired_key = expired_key.decode()

            if not expired_key.startswith(PENDING_TTL_KEY_PREFIX):
                continue

            event_id = expired_key[len(PENDING_TTL_KEY_PREFIX) :]
            logger.debug(f"[Redis] TTL expired for pending event {event_id}")

            try:
                await _handle_expired(
                    event_id, pending_store, events_repository
                )
            except Exception:
                logger.exception(
                    f"[Redis] Failed to handle expired pending event {event_id}"
                )

    except asyncio.CancelledError:
        await pubsub.punsubscribe(_EXPIRED_CHANNEL_PATTERN)
        await pubsub.aclose()
        logger.info("[Redis] TTL listener stopped")
        raise


async def _handle_expired(
    event_id: str,
    pending_store: PendingEventsStorePort,
    events_repository: EventsRepositoryPort,
) -> None:
    event = await pending_store.get_by_event_id(event_id)
    if event is None:
        # Уже обработано — exposure успел прийти раньше истечения TTL
        logger.debug(f"[Redis] Pending event {event_id} already removed, skip")
        return

    event.mark_as_rejected()
    await events_repository.save(event)
    await pending_store.delete_by_event_ids([event_id])

    logger.info(f"[Redis] Pending event {event_id} moved to DB as REJECTED")
