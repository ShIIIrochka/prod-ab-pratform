from uuid import UUID

from src.application.ports.notification_task_enqueuer import (
    NotificationTaskEnqueuerPort,
)


class FakeNotificationTaskEnqueuer(NotificationTaskEnqueuerPort):
    def __init__(self) -> None:
        self.enqueued: list[UUID] = []

    def enqueue(self, event_id: UUID) -> None:
        self.enqueued.append(event_id)
