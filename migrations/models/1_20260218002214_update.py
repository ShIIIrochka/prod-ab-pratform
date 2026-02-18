from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "events" (
    "id" UUID NOT NULL PRIMARY KEY,
    "event_type_key" VARCHAR(255) NOT NULL,
    "decision_id" VARCHAR(36) NOT NULL,
    "subject_id" VARCHAR(255) NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "props" JSONB NOT NULL,
    "attribution_status" VARCHAR(50) NOT NULL DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS "idx_events_event_t_bf1889" ON "events" ("event_type_key");
CREATE INDEX IF NOT EXISTS "idx_events_decisio_3b8e28" ON "events" ("decision_id");
CREATE INDEX IF NOT EXISTS "idx_events_subject_3ff429" ON "events" ("subject_id");
CREATE INDEX IF NOT EXISTS "idx_events_timesta_7c2666" ON "events" ("timestamp");
CREATE INDEX IF NOT EXISTS "idx_events_decisio_df5b94" ON "events" ("decision_id", "event_type_key");
CREATE INDEX IF NOT EXISTS "idx_events_subject_691cca" ON "events" ("subject_id", "timestamp");
CREATE INDEX IF NOT EXISTS "idx_events_event_t_c0797b" ON "events" ("event_type_key", "timestamp");
COMMENT ON COLUMN "events"."props" IS 'Event properties';
COMMENT ON COLUMN "events"."attribution_status" IS 'AttributionStatus enum: pending, attributed, rejected';
        CREATE TABLE IF NOT EXISTS "event_types" (
    "id" UUID NOT NULL PRIMARY KEY,
    "key" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(511) NOT NULL,
    "description" TEXT,
    "required_params" JSONB NOT NULL,
    "requires_exposure" BOOL NOT NULL DEFAULT False
);
CREATE INDEX IF NOT EXISTS "idx_event_types_key_ba505c" ON "event_types" ("key");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "events";
        DROP TABLE IF EXISTS "event_types";"""


MODELS_STATE = (
    "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"
    "uJrPV0+/F/ZtZwcw=="
)
