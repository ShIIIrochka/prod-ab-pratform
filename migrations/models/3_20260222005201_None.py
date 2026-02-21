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
CREATE INDEX IF NOT EXISTS "idx_event_types_key_ba505c" ON "event_types" ("key");
CREATE TABLE IF NOT EXISTS "feature_flags" (
    "key" VARCHAR(255) NOT NULL PRIMARY KEY,
    "value_type" VARCHAR(6) NOT NULL DEFAULT 'string',
    "default_value" JSONB NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "feature_flags"."value_type" IS 'STRING: string\nNUMBER: number\nBOOL: bool';
CREATE TABLE IF NOT EXISTS "guardrail_configs" (
    "id" UUID NOT NULL PRIMARY KEY,
    "experiment_id" VARCHAR(36) NOT NULL,
    "metric_key" VARCHAR(255) NOT NULL,
    "threshold" DOUBLE PRECISION NOT NULL,
    "observation_window_minutes" INT NOT NULL,
    "action" VARCHAR(50) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_guardrail_c_experim_2b0401" ON "guardrail_configs" ("experiment_id");
CREATE INDEX IF NOT EXISTS "idx_guardrail_c_metric__f30d3f" ON "guardrail_configs" ("metric_key");
COMMENT ON COLUMN "guardrail_configs"."experiment_id" IS 'Experiment UUID';
COMMENT ON COLUMN "guardrail_configs"."metric_key" IS 'Metric key';
COMMENT ON COLUMN "guardrail_configs"."threshold" IS 'Threshold value for guardrail trigger';
COMMENT ON COLUMN "guardrail_configs"."observation_window_minutes" IS 'Observation window in minutes';
COMMENT ON COLUMN "guardrail_configs"."action" IS 'GuardrailAction enum: pause or rollback_to_control';
CREATE TABLE IF NOT EXISTS "guardrail_triggers" (
    "id" UUID NOT NULL PRIMARY KEY,
    "experiment_id" VARCHAR(36) NOT NULL,
    "metric_key" VARCHAR(255),
    "threshold" DOUBLE PRECISION NOT NULL,
    "observation_window_minutes" INT NOT NULL,
    "action" VARCHAR(50) NOT NULL,
    "actual_value" DOUBLE PRECISION NOT NULL,
    "triggered_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_guardrail_t_experim_487a7b" ON "guardrail_triggers" ("experiment_id");
CREATE INDEX IF NOT EXISTS "idx_guardrail_t_metric__99485b" ON "guardrail_triggers" ("metric_key");
CREATE INDEX IF NOT EXISTS "idx_guardrail_t_trigger_7e0dc7" ON "guardrail_triggers" ("triggered_at");
COMMENT ON COLUMN "guardrail_triggers"."experiment_id" IS 'Experiment UUID';
COMMENT ON COLUMN "guardrail_triggers"."metric_key" IS 'Metric key';
COMMENT ON COLUMN "guardrail_triggers"."threshold" IS 'Threshold value';
COMMENT ON COLUMN "guardrail_triggers"."observation_window_minutes" IS 'Observation window in minutes';
COMMENT ON COLUMN "guardrail_triggers"."action" IS 'GuardrailAction enum: pause or rollback_to_control';
COMMENT ON COLUMN "guardrail_triggers"."actual_value" IS 'Actual metric value at the time of trigger';
COMMENT ON COLUMN "guardrail_triggers"."triggered_at" IS 'Timestamp when guardrail was triggered';
CREATE TABLE IF NOT EXISTS "metrics" (
    "key" VARCHAR(255) NOT NULL PRIMARY KEY,
    "name" VARCHAR(500) NOT NULL,
    "calculation_rule" TEXT NOT NULL,
    "description" TEXT,
    "aggregation_unit" VARCHAR(10) NOT NULL DEFAULT 'event'
);
COMMENT ON COLUMN "metrics"."key" IS 'Metric key (primary identifier)';
COMMENT ON COLUMN "metrics"."name" IS 'Human-readable metric name';
COMMENT ON COLUMN "metrics"."calculation_rule" IS 'Metric calculation rule';
COMMENT ON COLUMN "metrics"."description" IS 'Metric description';
COMMENT ON COLUMN "metrics"."aggregation_unit" IS 'Aggregation unit: event or user';
CREATE TABLE IF NOT EXISTS "users" (
    "id" VARCHAR(63) NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "role" VARCHAR(12) NOT NULL DEFAULT 'viewer',
    "approval_group" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."role" IS 'ADMIN: admin\nEXPERIMENTER: experimenter\nAPPROVER: approver\nVIEWER: viewer';
CREATE TABLE IF NOT EXISTS "experiments" (
    "id" UUID NOT NULL PRIMARY KEY,
    "flag_key" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "status" VARCHAR(9) NOT NULL DEFAULT 'draft',
    "version" INT NOT NULL DEFAULT 1,
    "audience_fraction" DOUBLE PRECISION NOT NULL,
    "targeting_rule" TEXT,
    "completion" JSONB,
    "rollback_to_control_active" BOOL NOT NULL DEFAULT False,
    "target_metric_key" VARCHAR(255),
    "metric_keys" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "owner_id" VARCHAR(63) NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_experiments_flag_ke_efbf3d" ON "experiments" ("flag_key");
CREATE INDEX IF NOT EXISTS "idx_experiments_status_2d66b5" ON "experiments" ("status");
COMMENT ON COLUMN "experiments"."status" IS 'DRAFT: draft\nON_REVIEW: on_review\nAPPROVED: approved\nRUNNING: running\nPAUSED: paused\nCOMPLETED: completed\nARCHIVED: archived\nREJECTED: rejected';
CREATE TABLE IF NOT EXISTS "approvals" (
    "id" UUID NOT NULL PRIMARY KEY,
    "comment" TEXT,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "experiment_id" UUID NOT NULL REFERENCES "experiments" ("id") ON DELETE CASCADE,
    "user_id" VARCHAR(63) NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_approvals_experim_16842d" ON "approvals" ("experiment_id", "user_id");
CREATE TABLE IF NOT EXISTS "variants" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "value" JSONB NOT NULL,
    "weight" DOUBLE PRECISION NOT NULL,
    "is_control" BOOL NOT NULL,
    "experiment_id" UUID NOT NULL REFERENCES "experiments" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_variants_experim_cbfe81" UNIQUE ("experiment_id", "name")
);
CREATE TABLE IF NOT EXISTS "decisions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "flag_key" VARCHAR(255) NOT NULL,
    "value" JSONB NOT NULL,
    "experiment_version" INT,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "experiment_id" UUID REFERENCES "experiments" ("id") ON DELETE SET NULL,
    "user_id" VARCHAR(63) NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT,
    "variant_id" UUID REFERENCES "variants" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_decisions_flag_ke_88aafb" ON "decisions" ("flag_key");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
