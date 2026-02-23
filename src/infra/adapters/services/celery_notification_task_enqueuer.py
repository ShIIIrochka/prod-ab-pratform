import logging

from uuid import UUID

from src.application.ports.notification_task_enqueuer import (
    NotificationTaskEnqueuerPort,
)
from src.infra.adapters.celery import celery_app


logger = logging.getLogger(__name__)


class CeleryNotificationTaskEnqueuer(NotificationTaskEnqueuerPort):
    def enqueue(self, event_id: UUID) -> None:
        celery_app.send_task(
            "notifications.process_notification_event",
            args=[str(event_id)],
            task_id=str(event_id),
        )
        logger.debug("Enqueued notification task for event %s", event_id)
