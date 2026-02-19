from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guardrail_configs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "experiment_id" VARCHAR(36) NOT NULL,
    "metric_key" VARCHAR(255) NOT NULL,
    "threshold" DOUBLE PRECISION NOT NULL,
    "observation_window_minutes" INT NOT NULL,
    "action" VARCHAR(50) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_guardrail_configs_experiment_id" ON "guardrail_configs" ("experiment_id");
COMMENT ON COLUMN "guardrail_configs"."metric_key" IS 'Metric key to monitor';
COMMENT ON COLUMN "guardrail_configs"."threshold" IS 'Threshold value for guardrail trigger';
COMMENT ON COLUMN "guardrail_configs"."observation_window_minutes" IS 'Observation window in minutes';
COMMENT ON COLUMN "guardrail_configs"."action" IS 'GuardrailAction enum: pause or rollback_to_control';
        CREATE TABLE IF NOT EXISTS "guardrail_triggers" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "experiment_id" VARCHAR(36) NOT NULL,
    "metric_key" VARCHAR(255) NOT NULL,
    "threshold" DOUBLE PRECISION NOT NULL,
    "observation_window_minutes" INT NOT NULL,
    "action" VARCHAR(50) NOT NULL,
    "actual_value" DOUBLE PRECISION NOT NULL,
    "triggered_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_guardrail_triggers_experiment_id" ON "guardrail_triggers" ("experiment_id");
CREATE INDEX IF NOT EXISTS "idx_guardrail_triggers_triggered_at" ON "guardrail_triggers" ("triggered_at");
COMMENT ON COLUMN "guardrail_triggers"."metric_key" IS 'Metric key that triggered the guardrail';
COMMENT ON COLUMN "guardrail_triggers"."actual_value" IS 'Actual metric value at the time of trigger';
COMMENT ON COLUMN "guardrail_triggers"."triggered_at" IS 'Timestamp when guardrail was triggered';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "guardrail_triggers";
        DROP TABLE IF EXISTS "guardrail_configs";
    """
