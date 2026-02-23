"""NotificationEventProcessor: application service for processing notification events.

Called by the Celery worker (infra layer) after it loads event_id from the queue.
No Celery/DB/Redis details here — only ports and domain objects.

Processing flow per event:
1. Load the NotificationEvent from the dedup store.
2. Find all matching NotificationRules.
3. For each rule:
   a. Skip if delivery already SENT (idempotency on retry).
   b. Check rate limit; record SKIPPED_RATE_LIMITED delivery if blocked.
   c. Load channel config; skip if missing or disabled.
   d. Resolve the channel adapter from the registry.
   e. Create/reuse delivery record.
   f. Format message and send.
   g. Update delivery status (SENT / FAILED / PERMANENT_FAILED).
"""

import logging

from uuid import UUID

from src.application.ports.notification_channel import NotificationChannelPort
from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.application.ports.notification_deliveries_repository import (
    NotificationDeliveriesRepositoryPort,
)
from src.application.ports.notification_events_repository import (
    NotificationEventsRepositoryPort,
)
from src.application.ports.notification_rate_limiter import (
    NotificationRateLimiterPort,
)
from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.application.services.notification_message_formatter import (
    format_notification_message,
)
from src.domain.entities.notification_delivery import (
    NotificationDelivery,
    new_notification_delivery,
)
from src.domain.entities.notification_rule import NotificationRule
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)
from src.domain.value_objects.notification_delivery_status import (
    NotificationDeliveryStatus,
)
from src.domain.value_objects.notification_event import NotificationEvent


logger = logging.getLogger(__name__)

# Type alias for the channel registry injected from infra.
ChannelRegistry = dict[NotificationChannelType, NotificationChannelPort]


class NotificationEventProcessor:
    def __init__(
        self,
        events_repository: NotificationEventsRepositoryPort,
        rules_repository: NotificationRulesRepositoryPort,
        channel_configs_repository: NotificationChannelConfigsRepositoryPort,
        deliveries_repository: NotificationDeliveriesRepositoryPort,
        rate_limiter: NotificationRateLimiterPort,
        channel_registry: ChannelRegistry,
    ) -> None:
        self._events_repo = events_repository
        self._rules_repo = rules_repository
        self._channel_configs_repo = channel_configs_repository
        self._deliveries_repo = deliveries_repository
        self._rate_limiter = rate_limiter
        self._channel_registry = channel_registry

    async def process(self, event_id: UUID) -> None:
        event = await self._events_repo.get_by_id(event_id)
        if event is None:
            logger.warning(
                "Notification event %s not found, skipping", event_id
            )
            return

        rules = await self._rules_repo.get_matching(
            event_type=event.event_type,
            entity_id=event.entity_id,
            payload=event.payload,
        )

        for rule in rules:
            await self._process_rule(event, rule)

    async def _process_rule(
        self, event: NotificationEvent, rule: NotificationRule
    ) -> None:
        existing_delivery = await self._deliveries_repo.get(
            event.event_id, rule.id
        )

        # Idempotency: already successfully sent on a previous attempt.
        if (
            existing_delivery
            and existing_delivery.status == NotificationDeliveryStatus.SENT
        ):
            logger.debug(
                "Delivery (event=%s rule=%s) already sent, skipping",
                event.event_id,
                rule.id,
            )
            return

        # Rate-limit check.
        if rule.rate_limit_seconds > 0:
            allowed = await self._rate_limiter.is_allowed(
                rule_id=rule.id,
                entity_id=event.entity_id,
                event_type=event.event_type,
                rate_limit_seconds=rule.rate_limit_seconds,
            )
            if not allowed:
                logger.info(
                    "Rate limited: rule=%s event=%s entity=%s",
                    rule.id,
                    event.event_type,
                    event.entity_id,
                )
                if existing_delivery is None:
                    delivery_ = new_notification_delivery(
                        event.event_id, rule.id, rule.channel_config_id
                    )
                    delivery_.mark_rate_limited()
                    await self._deliveries_repo.save(delivery_)
                return

        # Load channel config.
        channel_config = await self._channel_configs_repo.get_by_id(
            rule.channel_config_id
        )
        if channel_config is None or not channel_config.enabled:
            logger.warning(
                "Channel config %s not found or disabled, skipping rule %s",
                rule.channel_config_id,
                rule.id,
            )
            return

        channel = self._channel_registry.get(channel_config.type)
        if channel is None:
            logger.error(
                "No channel adapter for type %s (rule %s)",
                channel_config.type,
                rule.id,
            )
            return

        # Create delivery record on first attempt; reuse on retries.
        delivery: NotificationDelivery | None = None
        if existing_delivery is None:
            delivery = new_notification_delivery(
                event.event_id, rule.id, rule.channel_config_id
            )
            await self._deliveries_repo.save(delivery)
        else:
            delivery = existing_delivery

        message = format_notification_message(event, rule)

        try:
            await channel.send(
                message=message, webhook_url=channel_config.webhook_url
            )
            delivery.mark_sent()
            await self._deliveries_repo.save(delivery)
            logger.info(
                "Notification sent: event=%s rule=%s channel=%s",
                event.event_id,
                rule.id,
                channel_config.type,
            )
        except Exception as exc:
            delivery.mark_failed(str(exc))
            await self._deliveries_repo.save(delivery)
            logger.warning(
                "Channel send failed: event=%s rule=%s error=%s",
                event.event_id,
                rule.id,
                exc,
            )
            raise
