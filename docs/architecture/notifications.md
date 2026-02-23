# Notification Platform — Architecture

## Overview

The Notification Platform reacts to experiment lifecycle events and guardrail triggers,
delivering messages to configured channels (Slack, Telegram) via webhooks.

**Key properties:**
- Production-ready: deduplication, idempotent delivery, retriable sends, error logging.
- Scalable: background processing via Celery workers, decoupled from the API request path.
- Extensible: adding a new channel (e.g. Email) requires only a new adapter + DI registration — no core logic changes.
- Rate-limited per `(rule_id, entity_id, event_type)` via Redis atomic SET NX EX.

---

## C4 Component Diagram — Notification Module

```mermaid
C4Component
    title Notification Module — Component Diagram

    Container_Boundary(api, "AB Platform API (FastAPI)") {
        Component(lifecycle_uc, "Lifecycle UseCases", "Python", "launch/pause/approve/reject/complete/archive experiment")
        Component(guardrail_uc, "CheckGuardrailsUseCase", "Python", "Runs on schedule; checks metric thresholds")
        Component(dispatcher, "NotificationDispatcher", "Python/Service", "Dedup + enqueue notification events")
        Component(notif_api, "Notifications REST API", "FastAPI Router", "CRUD for channel configs, rules; delivery history")
    }

    Container_Boundary(workers, "Celery Worker") {
        Component(notif_task, "process_notification_event", "Celery Task", "Rule matching, rate limit, channel send, delivery recording")
    }

    Container_Boundary(infra, "Infrastructure") {
        ComponentDb(pg, "PostgreSQL", "DB", "notification_channel_configs, notification_rules, notification_events, notification_deliveries")
        ComponentDb(redis, "Redis", "Cache/Broker", "Celery broker; rate-limit keys (SET NX EX)")
    }

    Container_Boundary(channels, "Channel Adapters") {
        Component(slack, "SlackWebhookChannel", "httpx", "POST to Slack Incoming Webhook URL")
        Component(telegram, "TelegramWebhookChannel", "httpx", "POST to Telegram Bot API sendMessage")
    }

    Rel(lifecycle_uc, dispatcher, "dispatch(NotificationEvent)")
    Rel(guardrail_uc, dispatcher, "dispatch(NotificationEvent)")
    Rel(dispatcher, pg, "try_insert(event) — dedup via unique(event_id)")
    Rel(dispatcher, redis, "send_task(event_id) via Celery broker")
    Rel(notif_task, pg, "load event, rules, channel configs; save delivery")
    Rel(notif_task, redis, "rate-limit check SET NX EX")
    Rel(notif_task, slack, "send(message, webhook_url)")
    Rel(notif_task, telegram, "send(message, webhook_url)")
    Rel(notif_api, pg, "CRUD notification_rules and notification_channel_configs")
```

---

## Sequence Diagram: GuardrailTriggered → Notification

```mermaid
sequenceDiagram
    participant Worker as GuardrailCheckerWorker
    participant UC as CheckGuardrailsUseCase
    participant ExpRepo as ExperimentsRepository
    participant TrigRepo as GuardrailTriggersRepository
    participant UoW as UnitOfWork (PostgreSQL)
    participant Dispatcher as NotificationDispatcher
    participant EventRepo as NotificationEventsRepository
    participant Celery as Celery Broker (Redis)
    participant Task as process_notification_event (Celery Worker)
    participant RulesRepo as NotificationRulesRepository
    participant RateLimiter as RedisRateLimiter
    participant DelivRepo as NotificationDeliveriesRepository
    participant Channel as SlackWebhookChannel / TelegramWebhookChannel

    Worker->>UC: execute()
    UC->>ExpRepo: get_by_id(experiment_id)
    UC->>MetricAgg: get_value(experiment_id, metric, window)
    Note over UC: actual_value > threshold → guardrail triggered

    UC->>UoW: BEGIN
    UC->>TrigRepo: save(GuardrailTrigger)
    UC->>ExpRepo: save(experiment with PAUSED status)
    UC->>UoW: COMMIT

    UC->>Dispatcher: dispatch(NotificationEvent{guardrail.triggered, ...})
    Dispatcher->>EventRepo: try_insert(event) — INSERT with unique(event_id)
    alt event_id already exists (duplicate)
        EventRepo-->>Dispatcher: False (skip)
    else new event
        EventRepo-->>Dispatcher: True
        Dispatcher->>Celery: send_task("process_notification_event", event_id, task_id=event_id)
    end

    Note over Celery,Task: Celery picks up task (async, non-blocking)

    Task->>EventRepo: get_by_id(event_id)
    Task->>RulesRepo: get_matching(event_type, entity_id, payload)
    loop For each matching rule
        Task->>RateLimiter: is_allowed(rule_id, entity_id, event_type, rate_limit_seconds)
        alt Rate limited
            Task->>DelivRepo: save(delivery{status=SKIPPED_RATE_LIMITED})
        else Allowed
            Task->>DelivRepo: save(delivery{status=PENDING})
            Task->>Channel: send(message, webhook_url)
            alt Success
                Task->>DelivRepo: save(delivery{status=SENT})
            else Network error (retryable)
                Task->>DelivRepo: save(delivery{status=FAILED, attempt++})
                Task-->>Celery: retry(countdown=backoff)
            else Max retries exceeded
                Task->>DelivRepo: save(delivery{status=PERMANENT_FAILED})
            end
        end
    end
```

---

## Deduplication Strategy

Without the Outbox pattern (per project requirements), the following two-level deduplication is used:

1. **Event-level dedup** (`notification_events.id` — primary key = deterministic UUID5):
   - Generated as `uuid5(NAMESPACE, f"{event_type}:{entity_id}:{version}")`.
   - `try_insert()` uses the unique PK to silently no-op on duplicate inserts.
   - If the insert fails (duplicate), the dispatcher does NOT enqueue the Celery task.

2. **Delivery-level idempotency** (`notification_deliveries` unique on `(event_id, rule_id)`):
   - Even if the Celery task runs twice (rare: duplicate enqueue, worker restart), it checks the existing delivery record and skips `SENT` ones.

**Known limitation (FX-2):** If the application crashes between the DB `INSERT INTO notification_events` commit and the `celery.send_task()` call, the event is persisted but the Celery task is never enqueued. This event will be silently lost unless:
- A periodic reconciliation job is added (not implemented) to re-enqueue unprocessed events.
- The Outbox pattern is adopted (explicitly excluded by project requirements).

---

## Rate Limiting

- Redis key: `notif:rl:{rule_id}:{entity_id}:{event_type}`
- Atomic: `SET key 1 NX EX {rate_limit_seconds}` — first call acquires the lock, subsequent calls within the window are blocked.
- `rate_limit_seconds = 0` disables rate limiting for a rule.
- On rate-limited delivery, a `NotificationDelivery` record is saved with `status = SKIPPED_RATE_LIMITED` for audit purposes.

---

## Adding a New Channel (e.g. Email)

1. Create `src/infra/adapters/channels/email_channel.py` implementing `NotificationChannelPort`.
2. Add `EMAIL = "email"` to `NotificationChannelType`.
3. Register in `src/infra/tasks/notifications.py`'s `channel_registry`:
   ```python
   channel_registry = {
       NotificationChannelType.SLACK: SlackWebhookChannel(),
       NotificationChannelType.TELEGRAM: TelegramWebhookChannel(),
       NotificationChannelType.EMAIL: EmailChannel(smtp_config=...),
   }
   ```
4. **No changes needed** to domain logic, dispatcher, or repositories.
