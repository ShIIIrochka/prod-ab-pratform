# AB Platform — Operations Runbook

## Prerequisites

- Python 3.14+, `uv` package manager
- PostgreSQL running (default: `localhost:5432`, user `postgres`, password `postgres`)
- Redis running (default: `localhost:6379`)
- Environment variables configured (see `.env.example` or set directly)

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | `postgres` | PostgreSQL password |
| `DB_NAME` | `ab_platform` | Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (broker + rate limiter) |
| `JWT_SECRET` | — | JWT signing secret (required) |
| `JWT_ALG` | `HS256` | JWT algorithm |
| `JWT_ACCESS_EXPIRES` | `3600` | Access token TTL (seconds) |
| `JWT_REFRESH_EXPIRES` | `86400` | Refresh token TTL (seconds) |
| `GUARDRAIL_CHECK_INTERVAL_SECONDS` | `60` | How often guardrail worker checks metrics |

---

## Starting Services

### 1. Run Migrations

```bash
# Apply all pending Aerich migrations
uv run aerich upgrade
```

### 2. Start the API Server

```bash
# Using granian (production)
uv run granian --interface asgi src.main:app --host 0.0.0.0 --port 8000

# Or using uvicorn (development)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Celery Worker (for Notifications)

The Celery worker processes notification events asynchronously.

```bash
# Start worker with default concurrency (auto = number of CPUs)
celery -A src.infra.celery_app worker -l info

# Or with explicit concurrency
celery -A src.infra.celery_app worker -l info --concurrency=4

# Start with a named queue (recommended for production)
celery -A src.infra.celery_app worker -l info -Q celery --concurrency=2
```

### 4. Start Celery Flower (optional monitoring UI)

```bash
# Install flower if needed
uv add flower

celery -A src.infra.celery_app flower --port=5555
# Open http://localhost:5555
```

---

## Running Tests

### Unit Tests (no external services required)

```bash
uv run pytest tests/unit/ -v
```

### E2E Tests (requires PostgreSQL + Redis)

```bash
# Set up environment (or export variables)
export DB_HOST=localhost DB_PORT=5432 DB_USER=postgres DB_PASSWORD=postgres
export REDIS_HOST=localhost REDIS_PORT=6379

uv run pytest tests/e2e/ -v
```

### All Tests

```bash
uv run pytest -v
```

---

## Docker Compose (Quick Start)

```yaml
# docker-compose.yml (example)
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ab_platform
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: uv run granian --interface asgi src.main:app --host 0.0.0.0 --port 8000
    environment:
      DB_HOST: postgres
      DB_USER: postgres
      DB_PASSWORD: postgres
      DB_NAME: ab_platform
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: change-me-in-production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery_worker:
    build: .
    command: celery -A src.infra.celery_app worker -l info --concurrency=2
    environment:
      DB_HOST: postgres
      DB_USER: postgres
      DB_PASSWORD: postgres
      DB_NAME: ab_platform
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
```

---

## Notification Platform Setup

After the API and Celery worker are running:

### 1. Connect a Channel

**Telegram** — provide bot token (from [@BotFather](https://t.me/BotFather)) and chat/group ID:

```bash
curl -X POST http://localhost:8000/notifications/telegram/connect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Telegram",
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "-1001234567890"
  }'
```

To get `chat_id`: add the bot to the group/channel, send a message, then call `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `chat.id` from the response.

**Slack** — provide Incoming Webhook URL (from Slack app settings → Incoming Webhooks → Add to Workspace):

```bash
curl -X POST http://localhost:8000/notifications/slack/connect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Alerts",
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  }'
```

**Disconnect** (removes channel config and all associated rules):

```bash
# Telegram
curl -X DELETE "http://localhost:8000/notifications/telegram/{config_id}" \
  -H "Authorization: Bearer $TOKEN"

# Slack
curl -X DELETE "http://localhost:8000/notifications/slack/{config_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Legacy: Create a Channel Config (generic)

Use the generic endpoint if you prefer to pass the full webhook URL directly:

```bash
curl -X POST http://localhost:8000/notifications/channel-configs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "slack",
    "name": "Team Alerts",
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "enabled": true
  }'
```

### 3. Create a Notification Rule

```bash
# Notify on all guardrail triggers
curl -X POST http://localhost:8000/notifications/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "guardrail.triggered",
    "channel_config_id": "<channel_config_id>",
    "enabled": true,
    "rate_limit_seconds": 300
  }'

# Notify on experiment launched (wildcard — all experiments)
curl -X POST http://localhost:8000/notifications/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "experiment.launched",
    "channel_config_id": "<channel_config_id>",
    "enabled": true,
    "rate_limit_seconds": 0
  }'
```

### 4. Check Delivery History

```bash
curl -X GET "http://localhost:8000/notifications/deliveries?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Experiment Versioning

All configuration changes are stored as version snapshots.

### View Version History

```bash
curl -X GET "http://localhost:8000/experiments/{experiment_id}/versions" \
  -H "Authorization: Bearer $TOKEN"
```

### View Specific Version Snapshot

```bash
curl -X GET "http://localhost:8000/experiments/{experiment_id}/versions/2" \
  -H "Authorization: Bearer $TOKEN"
```
