import logging

from src.application.ports.notification_events_repository import (
    NotificationEventsRepositoryPort,
)
from src.application.ports.notification_task_enqueuer import (
    NotificationTaskEnqueuerPort,
)
from src.domain.value_objects.notification_event import NotificationEvent


logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(
        self,
        events_repository: NotificationEventsRepositoryPort,
        task_enqueuer: NotificationTaskEnqueuerPort,
    ) -> None:
        self._events_repository = events_repository
        self._task_enqueuer = task_enqueuer

    async def dispatch(self, event: NotificationEvent) -> None:
        """Persist event (dedup) then enqueue background task."""
        try:
            inserted = await self._events_repository.try_insert(event)
        except Exception:
            logger.exception(
                "Failed to persist notification event %s (type=%s), skipping dispatch",
                event.event_id,
                event.event_type,
            )
            return

        if not inserted:
            logger.debug(
                "Notification event %s already processed, skipping",
                event.event_id,
            )
            return

        try:
            self._task_enqueuer.enqueue(event.event_id)
            logger.info(
                "Notification task enqueued for event %s (type=%s entity=%s)",
                event.event_id,
                event.event_type,
                event.entity_id,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue notification task for event %s",
                event.event_id,
            )
