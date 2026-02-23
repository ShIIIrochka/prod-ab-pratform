from __future__ import annotations

import logging

from src.application.ports.domain_events import HasDomainEvents
from src.application.services.notification_dispatcher import (
    NotificationDispatcher,
)
from src.domain.events.experiment import (
    ExperimentEventType,
    ExperimentStatusChanged,
    GuardrailTriggered,
)
from src.domain.value_objects.notification_event import (
    NotificationEvent,
    make_notification_event_id,
)
from src.domain.value_objects.notification_event_type import (
    NotificationEventType,
)


logger = logging.getLogger(__name__)

_EXPERIMENT_EVENT_MAP: dict[ExperimentEventType, str] = {
    ExperimentEventType.SENT_TO_REVIEW: NotificationEventType.EXPERIMENT_SENT_TO_REVIEW,
    ExperimentEventType.APPROVED: NotificationEventType.EXPERIMENT_APPROVED,
    ExperimentEventType.CHANGES_REQUESTED: NotificationEventType.EXPERIMENT_CHANGES_REQUESTED,
    ExperimentEventType.REJECTED: NotificationEventType.EXPERIMENT_REJECTED,
    ExperimentEventType.LAUNCHED: NotificationEventType.EXPERIMENT_LAUNCHED,
    ExperimentEventType.PAUSED: NotificationEventType.EXPERIMENT_PAUSED,
    ExperimentEventType.COMPLETED: NotificationEventType.EXPERIMENT_COMPLETED,
    ExperimentEventType.ARCHIVED: NotificationEventType.EXPERIMENT_ARCHIVED,
}


def _to_notification_event(
    domain_event: ExperimentStatusChanged | GuardrailTriggered,
) -> NotificationEvent | None:
    if isinstance(domain_event, ExperimentStatusChanged):
        notif_type = _EXPERIMENT_EVENT_MAP.get(domain_event.event_type)
        if notif_type is None:
            logger.warning(
                "No notification mapping for event type %s",
                domain_event.event_type,
            )
            return None
        event_id = make_notification_event_id(
            notif_type, domain_event.experiment_id, domain_event.version
        )
        payload: dict = {
            "experiment_name": domain_event.experiment_name,
            "flag_key": domain_event.flag_key,
            "owner_id": domain_event.owner_id,
            "status": domain_event.status,
            "version": domain_event.version,
        }
        payload.update(domain_event.extra)
        return NotificationEvent(
            event_id=event_id,
            event_type=notif_type,
            entity_type="experiment",
            entity_id=domain_event.experiment_id,
            payload=payload,
        )

    if isinstance(domain_event, GuardrailTriggered):
        notif_type = NotificationEventType.GUARDRAIL_TRIGGERED
        event_id = make_notification_event_id(
            notif_type,
            domain_event.experiment_id,
            int(domain_event.triggered_at.timestamp()),
        )
        return NotificationEvent(
            event_id=event_id,
            event_type=notif_type,
            entity_type="experiment",
            entity_id=domain_event.experiment_id,
            payload={
                "experiment_name": domain_event.experiment_name,
                "flag_key": domain_event.flag_key,
                "owner_id": domain_event.owner_id,
                "metric_key": domain_event.metric_key,
                "threshold": domain_event.threshold,
                "actual_value": domain_event.actual_value,
                "action": domain_event.action,
                "triggered_at": domain_event.triggered_at.isoformat(),
            },
        )

    logger.warning("Unknown domain event type: %s", type(domain_event).__name__)
    return None


class DomainEventPublisher:
    def __init__(self, dispatcher: NotificationDispatcher) -> None:
        self._dispatcher = dispatcher

    async def publish(
        self, domain_event: ExperimentStatusChanged | GuardrailTriggered
    ) -> None:
        notif_event = _to_notification_event(domain_event)
        if notif_event is not None:
            await self._dispatcher.dispatch(notif_event)

    async def publish_from(self, aggregate: HasDomainEvents) -> None:
        for event in aggregate.pop_domain_events():
            await self.publish(event)
