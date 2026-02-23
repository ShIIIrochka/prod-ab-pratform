from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "experiment_versions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "version" INT NOT NULL,
    "snapshot" JSONB NOT NULL,
    "changed_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "changed_by" VARCHAR(255),
    "experiment_id" UUID NOT NULL REFERENCES "experiments" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_experiment__experim_558c2b" UNIQUE ("experiment_id", "version")
);
CREATE INDEX IF NOT EXISTS "idx_experiment__experim_22aec1" ON "experiment_versions" ("experiment_id");
        CREATE TABLE IF NOT EXISTS "notification_channel_configs" (
    "id" UUID NOT NULL PRIMARY KEY,
    "type" VARCHAR(50) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "webhook_url" TEXT NOT NULL,
    "enabled" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
        CREATE TABLE IF NOT EXISTS "notification_events" (
    "id" UUID NOT NULL PRIMARY KEY,
    "event_type" VARCHAR(100) NOT NULL,
    "entity_type" VARCHAR(100) NOT NULL,
    "entity_id" UUID NOT NULL,
    "payload" JSONB NOT NULL,
    "occurred_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "notification_events" IS 'Dedup table for notification events.';
        CREATE TABLE IF NOT EXISTS "notification_rules" (
    "id" UUID NOT NULL PRIMARY KEY,
    "event_type" VARCHAR(100) NOT NULL,
    "enabled" BOOL NOT NULL DEFAULT True,
    "experiment_id" UUID,
    "flag_key" VARCHAR(255),
    "owner_id" VARCHAR(255),
    "metric_key" VARCHAR(255),
    "severity" VARCHAR(50),
    "rate_limit_seconds" INT NOT NULL DEFAULT 0,
    "template" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "channel_config_id" UUID NOT NULL REFERENCES "notification_channel_configs" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_notificatio_event_t_afc729" ON "notification_rules" ("event_type", "enabled");
        CREATE TABLE IF NOT EXISTS "notification_deliveries" (
    "id" UUID NOT NULL PRIMARY KEY,
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "attempt_count" INT NOT NULL DEFAULT 0,
    "last_error" TEXT,
    "sent_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "channel_config_id" UUID REFERENCES "notification_channel_configs" ("id") ON DELETE SET NULL,
    "event_id" UUID NOT NULL REFERENCES "notification_events" ("id") ON DELETE CASCADE,
    "rule_id" UUID REFERENCES "notification_rules" ("id") ON DELETE SET NULL,
    CONSTRAINT "uid_notificatio_event_i_256ded" UNIQUE ("event_id", "rule_id")
);
CREATE INDEX IF NOT EXISTS "idx_notificatio_event_i_78d72d" ON "notification_deliveries" ("event_id");
CREATE INDEX IF NOT EXISTS "idx_notificatio_status_9ca8f4" ON "notification_deliveries" ("status");
CREATE INDEX IF NOT EXISTS "idx_notificatio_created_07e5a2" ON "notification_deliveries" ("created_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "notification_channel_configs";
        DROP TABLE IF EXISTS "notification_deliveries";
        DROP TABLE IF EXISTS "notification_events";
        DROP TABLE IF EXISTS "notification_rules";
        DROP TABLE IF EXISTS "experiment_versions";"""


MODELS_STATE = (
    "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"
    "460dSY30++HRITEZZI1hIp4Qqu/sPy/H/mYXld"
)
