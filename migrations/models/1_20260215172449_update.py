from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_decisions_experim_56e0bc";
        DROP INDEX IF EXISTS "idx_decisions_subject_5c2d86";
        DROP INDEX IF EXISTS "idx_decisions_subject_e7c7f3";
        DROP INDEX IF EXISTS "idx_approvals_experim_48632a";
        ALTER TABLE "approvals" ALTER COLUMN "timestamp" TYPE TIMESTAMPTZ USING "timestamp"::TIMESTAMPTZ;
        COMMENT ON COLUMN "approvals"."timestamp" IS NULL;
        COMMENT ON COLUMN "approvals"."comment" IS NULL;
        ALTER TABLE "approvals" ALTER COLUMN "experiment_id" TYPE UUID USING "experiment_id"::UUID;
        COMMENT ON COLUMN "approvals"."experiment_id" IS NULL;
        ALTER TABLE "approvals" ALTER COLUMN "user_id" TYPE VARCHAR(63) USING "user_id"::VARCHAR(63);
        COMMENT ON COLUMN "approvals"."user_id" IS NULL;
        ALTER TABLE "decisions" ADD "user_id" VARCHAR(63) NOT NULL;
        ALTER TABLE "decisions" DROP COLUMN "subject_id";
        ALTER TABLE "decisions" ALTER COLUMN "variant_id" TYPE UUID USING "variant_id"::UUID;
        COMMENT ON COLUMN "decisions"."variant_id" IS NULL;
        COMMENT ON COLUMN "decisions"."value" IS NULL;
        ALTER TABLE "decisions" ALTER COLUMN "timestamp" TYPE TIMESTAMPTZ USING "timestamp"::TIMESTAMPTZ;
        COMMENT ON COLUMN "decisions"."timestamp" IS NULL;
        ALTER TABLE "decisions" ALTER COLUMN "experiment_id" TYPE UUID USING "experiment_id"::UUID;
        COMMENT ON COLUMN "decisions"."experiment_id" IS NULL;
        COMMENT ON COLUMN "decisions"."flag_key" IS NULL;
        COMMENT ON COLUMN "decisions"."experiment_version" IS NULL;
        ALTER TABLE "experiments" ADD "completion" JSONB;
        ALTER TABLE "experiments" ADD "rollback_to_control_active" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "approvals" ADD CONSTRAINT "fk_approval_users_4ed95201" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE RESTRICT;
        ALTER TABLE "approvals" ADD CONSTRAINT "fk_approval_experime_ee0d2047" FOREIGN KEY ("experiment_id") REFERENCES "experiments" ("id") ON DELETE CASCADE;
        ALTER TABLE "decisions" ADD CONSTRAINT "fk_decision_users_bceb2399" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE RESTRICT;
        ALTER TABLE "decisions" ADD CONSTRAINT "fk_decision_experime_eb9a5425" FOREIGN KEY ("experiment_id") REFERENCES "experiments" ("id") ON DELETE SET NULL;
        ALTER TABLE "decisions" ADD CONSTRAINT "fk_decision_variants_6596b0bc" FOREIGN KEY ("variant_id") REFERENCES "variants" ("id") ON DELETE CASCADE;
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_decisions_variant_3825ec" ON "decisions" ("variant_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "decisions" DROP CONSTRAINT IF EXISTS "decisions_variant_id_key";
        DROP INDEX IF EXISTS "uid_decisions_variant_3825ec";
        ALTER TABLE "decisions" DROP CONSTRAINT IF EXISTS "fk_decision_variants_6596b0bc";
        ALTER TABLE "decisions" DROP CONSTRAINT IF EXISTS "fk_decision_experime_eb9a5425";
        ALTER TABLE "decisions" DROP CONSTRAINT IF EXISTS "fk_decision_users_bceb2399";
        ALTER TABLE "approvals" DROP CONSTRAINT IF EXISTS "fk_approval_experime_ee0d2047";
        ALTER TABLE "approvals" DROP CONSTRAINT IF EXISTS "fk_approval_users_4ed95201";
        COMMENT ON COLUMN "approvals"."timestamp" IS 'Approval timestamp';
        ALTER TABLE "approvals" ALTER COLUMN "timestamp" TYPE TIMESTAMPTZ USING "timestamp"::TIMESTAMPTZ;
        COMMENT ON COLUMN "approvals"."comment" IS 'Optional approval comment';
        ALTER TABLE "approvals" ALTER COLUMN "experiment_id" TYPE VARCHAR(36) USING "experiment_id"::VARCHAR(36);
        COMMENT ON COLUMN "approvals"."experiment_id" IS 'Experiment UUID';
        COMMENT ON COLUMN "approvals"."user_id" IS 'Approver User UUID';
        ALTER TABLE "approvals" ALTER COLUMN "user_id" TYPE VARCHAR(36) USING "user_id"::VARCHAR(36);
        ALTER TABLE "decisions" ADD "subject_id" VARCHAR(255) NOT NULL;
        ALTER TABLE "decisions" DROP COLUMN "user_id";
        ALTER TABLE "decisions" ALTER COLUMN "variant_id" TYPE VARCHAR(255) USING "variant_id"::VARCHAR(255);
        COMMENT ON COLUMN "decisions"."variant_id" IS 'Variant ID if applied';
        COMMENT ON COLUMN "decisions"."value" IS 'Decision value';
        COMMENT ON COLUMN "decisions"."timestamp" IS 'Decision timestamp';
        ALTER TABLE "decisions" ALTER COLUMN "timestamp" TYPE TIMESTAMPTZ USING "timestamp"::TIMESTAMPTZ;
        ALTER TABLE "decisions" ALTER COLUMN "experiment_id" TYPE VARCHAR(36) USING "experiment_id"::VARCHAR(36);
        COMMENT ON COLUMN "decisions"."experiment_id" IS 'Experiment ID if applied';
        COMMENT ON COLUMN "decisions"."flag_key" IS 'Flag key';
        COMMENT ON COLUMN "decisions"."experiment_version" IS 'Experiment version at decision time';
        ALTER TABLE "experiments" DROP COLUMN "completion";
        ALTER TABLE "experiments" DROP COLUMN "rollback_to_control_active";
        COMMENT ON COLUMN "decisions"."subject_id" IS 'Subject ID';
        CREATE INDEX IF NOT EXISTS "idx_approvals_experim_48632a" ON "approvals" ("experiment_id");
        CREATE INDEX IF NOT EXISTS "idx_decisions_subject_e7c7f3" ON "decisions" ("subject_id", "flag_key");
        CREATE INDEX IF NOT EXISTS "idx_decisions_subject_5c2d86" ON "decisions" ("subject_id");
        CREATE INDEX IF NOT EXISTS "idx_decisions_experim_56e0bc" ON "decisions" ("experiment_id");"""


MODELS_STATE = (
    "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"
    "OpKmIzt9xf3wH1booww="
)
