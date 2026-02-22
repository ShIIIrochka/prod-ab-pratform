from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_guardrail_t_experim_487a7b";
        DROP INDEX IF EXISTS "idx_guardrail_t_metric__99485b";
        DROP INDEX IF EXISTS "idx_guardrail_t_metric__99485b";
        DROP INDEX IF EXISTS "idx_guardrail_c_experim_2b0401";
        DROP INDEX IF EXISTS "idx_guardrail_c_metric__f30d3f";
        DROP INDEX IF EXISTS "idx_guardrail_c_metric__f30d3f";
        DROP INDEX IF EXISTS "idx_events_subject_3ff429";
        DROP INDEX IF EXISTS "idx_events_decisio_3b8e28";
        DROP INDEX IF EXISTS "idx_decisions_flag_ke_88aafb";
        ALTER TABLE "decisions" ADD "flag_id" VARCHAR(255) NOT NULL;
        ALTER TABLE "decisions" DROP COLUMN "flag_key";
        ALTER TABLE "events" ALTER COLUMN "decision_id" TYPE UUID USING "decision_id"::UUID;
        ALTER TABLE "events" ALTER COLUMN "subject_id" TYPE VARCHAR(63) USING "subject_id"::VARCHAR(63);
        ALTER TABLE "experiments" RENAME COLUMN "target_metric_key" TO "target_metric_id";
        ALTER TABLE "guardrail_configs" ADD "metric_id" VARCHAR(255) NOT NULL;
        ALTER TABLE "guardrail_configs" DROP COLUMN "metric_key";
        ALTER TABLE "guardrail_configs" ALTER COLUMN "experiment_id" TYPE UUID USING "experiment_id"::UUID;
        COMMENT ON COLUMN "guardrail_configs"."experiment_id" IS NULL;
        ALTER TABLE "guardrail_triggers" ADD "metric_id" VARCHAR(255);
        ALTER TABLE "guardrail_triggers" DROP COLUMN "metric_key";
        ALTER TABLE "guardrail_triggers" ALTER COLUMN "experiment_id" TYPE UUID USING "experiment_id"::UUID;
        COMMENT ON COLUMN "guardrail_triggers"."experiment_id" IS NULL;
        ALTER TABLE "decisions" ADD CONSTRAINT "fk_decision_feature__05c09990" FOREIGN KEY ("flag_id") REFERENCES "feature_flags" ("key") ON DELETE RESTRICT;
        ALTER TABLE "events" ADD CONSTRAINT "fk_events_decision_3756f67d" FOREIGN KEY ("decision_id") REFERENCES "decisions" ("id") ON DELETE RESTRICT;
        ALTER TABLE "events" ADD CONSTRAINT "fk_events_users_ba53b361" FOREIGN KEY ("subject_id") REFERENCES "users" ("id") ON DELETE RESTRICT;
        ALTER TABLE "experiments" ADD CONSTRAINT "fk_experime_metrics_a28d7314" FOREIGN KEY ("target_metric_id") REFERENCES "metrics" ("key") ON DELETE SET NULL;
        ALTER TABLE "guardrail_configs" ADD CONSTRAINT "fk_guardrai_experime_0ead2ba7" FOREIGN KEY ("experiment_id") REFERENCES "experiments" ("id") ON DELETE CASCADE;
        ALTER TABLE "guardrail_configs" ADD CONSTRAINT "fk_guardrai_metrics_0b2812f6" FOREIGN KEY ("metric_id") REFERENCES "metrics" ("key") ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS "idx_guardrail_c_metric__162178" ON "guardrail_configs" ("metric_id");
        ALTER TABLE "guardrail_triggers" ADD CONSTRAINT "fk_guardrai_experime_a51a5b97" FOREIGN KEY ("experiment_id") REFERENCES "experiments" ("id") ON DELETE CASCADE;
        ALTER TABLE "guardrail_triggers" ADD CONSTRAINT "fk_guardrai_metrics_a69e5502" FOREIGN KEY ("metric_id") REFERENCES "metrics" ("key") ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS "idx_guardrail_t_metric__5f08b0" ON "guardrail_triggers" ("metric_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_guardrail_t_metric__5f08b0";
        ALTER TABLE "guardrail_triggers" DROP CONSTRAINT IF EXISTS "fk_guardrai_metrics_a69e5502";
        ALTER TABLE "guardrail_triggers" DROP CONSTRAINT IF EXISTS "fk_guardrai_experime_a51a5b97";
        DROP INDEX IF EXISTS "idx_guardrail_c_metric__162178";
        ALTER TABLE "guardrail_configs" DROP CONSTRAINT IF EXISTS "fk_guardrai_metrics_0b2812f6";
        ALTER TABLE "guardrail_configs" DROP CONSTRAINT IF EXISTS "fk_guardrai_experime_0ead2ba7";
        ALTER TABLE "experiments" DROP CONSTRAINT IF EXISTS "fk_experime_metrics_a28d7314";
        ALTER TABLE "decisions" DROP CONSTRAINT IF EXISTS "fk_decision_feature__05c09990";
        ALTER TABLE "events" DROP CONSTRAINT IF EXISTS "fk_events_users_ba53b361";
        ALTER TABLE "events" DROP CONSTRAINT IF EXISTS "fk_events_decision_3756f67d";
        ALTER TABLE "events" ALTER COLUMN "decision_id" TYPE VARCHAR(36) USING "decision_id"::VARCHAR(36);
        ALTER TABLE "events" ALTER COLUMN "subject_id" TYPE VARCHAR(255) USING "subject_id"::VARCHAR(255);
        ALTER TABLE "decisions" ADD "flag_key" VARCHAR(255) NOT NULL;
        ALTER TABLE "decisions" DROP COLUMN "flag_id";
        ALTER TABLE "experiments" RENAME COLUMN "target_metric_id" TO "target_metric_key";
        ALTER TABLE "guardrail_configs" ADD "metric_key" VARCHAR(255) NOT NULL;
        ALTER TABLE "guardrail_configs" DROP COLUMN "metric_id";
        ALTER TABLE "guardrail_configs" ALTER COLUMN "experiment_id" TYPE VARCHAR(36) USING "experiment_id"::VARCHAR(36);
        COMMENT ON COLUMN "guardrail_configs"."experiment_id" IS 'Experiment UUID';
        ALTER TABLE "guardrail_triggers" ADD "metric_key" VARCHAR(255);
        ALTER TABLE "guardrail_triggers" DROP COLUMN "metric_id";
        ALTER TABLE "guardrail_triggers" ALTER COLUMN "experiment_id" TYPE VARCHAR(36) USING "experiment_id"::VARCHAR(36);
        COMMENT ON COLUMN "guardrail_triggers"."experiment_id" IS 'Experiment UUID';
        COMMENT ON COLUMN "guardrail_configs"."metric_key" IS 'Metric key';
COMMENT ON COLUMN "guardrail_triggers"."metric_key" IS 'Metric key';
        CREATE INDEX IF NOT EXISTS "idx_events_decisio_3b8e28" ON "events" ("decision_id");
        CREATE INDEX IF NOT EXISTS "idx_events_subject_3ff429" ON "events" ("subject_id");
        CREATE INDEX IF NOT EXISTS "idx_decisions_flag_ke_88aafb" ON "decisions" ("flag_key");
        CREATE INDEX IF NOT EXISTS "idx_guardrail_c_metric__f30d3f" ON "guardrail_configs" ("metric_key");
        CREATE INDEX IF NOT EXISTS "idx_guardrail_c_metric__f30d3f" ON "guardrail_configs" ("metric_key");
        CREATE INDEX IF NOT EXISTS "idx_guardrail_c_experim_2b0401" ON "guardrail_configs" ("experiment_id");
        CREATE INDEX IF NOT EXISTS "idx_guardrail_t_metric__99485b" ON "guardrail_triggers" ("metric_key");
        CREATE INDEX IF NOT EXISTS "idx_guardrail_t_metric__99485b" ON "guardrail_triggers" ("metric_key");
        CREATE INDEX IF NOT EXISTS "idx_guardrail_t_experim_487a7b" ON "guardrail_triggers" ("experiment_id");"""


MODELS_STATE = (
    "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"
)
