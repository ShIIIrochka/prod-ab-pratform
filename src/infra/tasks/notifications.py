import asyncio
import logging

from typing import Any
from uuid import UUID

from celery import Task
from celery.signals import worker_process_init, worker_process_shutdown

from src.infra.adapters.celery import celery_app
from src.infra.adapters.config import _TORTOISE_MODULES, Config


logger = logging.getLogger(__name__)

_config = Config.get_config()


@worker_process_init.connect
def _init_worker_process(**_kwargs: Any) -> None:
    logger.info("Celery notification worker process initialised")


@worker_process_shutdown.connect
def _shutdown_worker_process(**_kwargs: Any) -> None:
    logger.info("Celery notification worker process shut down")


@celery_app.task(
    bind=True,
    name="notifications.process_notification_event",
    max_retries=_config.notification_task_max_retries,
    default_retry_delay=_config.notification_task_retry_backoff_seconds,
)
def process_notification_event(self: Task, event_id_str: str) -> None:
    asyncio.run(_async_process(self, UUID(event_id_str)))


async def _async_process(task: Task, event_id: UUID) -> None:
    from redis.asyncio import Redis
    from tortoise import Tortoise

    from src.application.services.notification_event_processor import (
        NotificationEventProcessor,
    )
    from src.domain.value_objects.notification_channel_type import (
        NotificationChannelType,
    )
    from src.infra.adapters.channels.slack_webhook_channel import (
        SlackWebhookChannel,
    )
    from src.infra.adapters.channels.telegram_webhook_channel import (
        TelegramWebhookChannel,
    )
    from src.infra.adapters.repositories.notification_channel_configs_repository import (
        NotificationChannelConfigsRepository,
    )
    from src.infra.adapters.repositories.notification_deliveries_repository import (
        NotificationDeliveriesRepository,
    )
    from src.infra.adapters.repositories.notification_events_repository import (
        NotificationEventsRepository,
    )
    from src.infra.adapters.repositories.notification_rules_repository import (
        NotificationRulesRepository,
    )
    from src.infra.adapters.services.redis_notification_rate_limiter import (
        RedisNotificationRateLimiter,
    )

    await Tortoise.init(db_url=_config.db_uri, modules=_TORTOISE_MODULES)
    redis = Redis.from_url(_config.redis_url, decode_responses=True)

    try:
        processor = NotificationEventProcessor(
            events_repository=NotificationEventsRepository(),
            rules_repository=NotificationRulesRepository(),
            channel_configs_repository=NotificationChannelConfigsRepository(),
            deliveries_repository=NotificationDeliveriesRepository(),
            rate_limiter=RedisNotificationRateLimiter(redis=redis),
            channel_registry={
                NotificationChannelType.SLACK: SlackWebhookChannel(),
                NotificationChannelType.TELEGRAM: TelegramWebhookChannel(),
            },
        )
        await processor.process(event_id)

    except Exception as exc:
        attempt = (task.request.retries or 0) + 1
        logger.warning(
            "Notification processing failed (attempt %d/%d): event=%s error=%s",
            attempt,
            _config.notification_task_max_retries,
            event_id,
            exc,
        )
        if attempt < _config.notification_task_max_retries:
            backoff = _config.notification_task_retry_backoff_seconds * (
                2 ** (attempt - 1)
            )
            raise task.retry(exc=exc, countdown=backoff)
        logger.error(
            "Permanently failed to process notification event %s", event_id
        )

    finally:
        await redis.aclose()
        await Tortoise.close_connections()
