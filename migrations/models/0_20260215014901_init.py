from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "approvals" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "experiment_id" VARCHAR(36) NOT NULL,
    "user_id" VARCHAR(36) NOT NULL,
    "comment" TEXT,
    "timestamp" TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_approvals_experim_48632a" ON "approvals" ("experiment_id");
CREATE INDEX IF NOT EXISTS "idx_approvals_experim_16842d" ON "approvals" ("experiment_id", "user_id");
COMMENT ON COLUMN "approvals"."id" IS 'Auto-increment ID';
COMMENT ON COLUMN "approvals"."experiment_id" IS 'Experiment UUID';
COMMENT ON COLUMN "approvals"."user_id" IS 'Approver User UUID';
COMMENT ON COLUMN "approvals"."comment" IS 'Optional approval comment';
COMMENT ON COLUMN "approvals"."timestamp" IS 'Approval timestamp';
COMMENT ON TABLE "approvals" IS 'Tortoise модель для одобрений эксперимента.';
CREATE TABLE IF NOT EXISTS "decisions" (
    "id" VARCHAR(36) NOT NULL PRIMARY KEY,
    "subject_id" VARCHAR(255) NOT NULL,
    "flag_key" VARCHAR(255) NOT NULL,
    "value" JSONB NOT NULL,
    "experiment_id" VARCHAR(36),
    "variant_id" VARCHAR(255),
    "experiment_version" INT,
    "timestamp" TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_decisions_subject_5c2d86" ON "decisions" ("subject_id");
CREATE INDEX IF NOT EXISTS "idx_decisions_flag_ke_88aafb" ON "decisions" ("flag_key");
CREATE INDEX IF NOT EXISTS "idx_decisions_experim_56e0bc" ON "decisions" ("experiment_id");
CREATE INDEX IF NOT EXISTS "idx_decisions_subject_e7c7f3" ON "decisions" ("subject_id", "flag_key");
COMMENT ON COLUMN "decisions"."id" IS 'Decision ID (UUID, deterministic)';
COMMENT ON COLUMN "decisions"."subject_id" IS 'Subject ID';
COMMENT ON COLUMN "decisions"."flag_key" IS 'Flag key';
COMMENT ON COLUMN "decisions"."value" IS 'Decision value';
COMMENT ON COLUMN "decisions"."experiment_id" IS 'Experiment ID if applied';
COMMENT ON COLUMN "decisions"."variant_id" IS 'Variant ID if applied';
COMMENT ON COLUMN "decisions"."experiment_version" IS 'Experiment version at decision time';
COMMENT ON COLUMN "decisions"."timestamp" IS 'Decision timestamp';
CREATE TABLE IF NOT EXISTS "feature_flags" (
    "key" VARCHAR(255) NOT NULL PRIMARY KEY,
    "value_type" VARCHAR(6) NOT NULL DEFAULT 'string',
    "default_value" JSONB NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "feature_flags"."value_type" IS 'STRING: string\nNUMBER: number\nBOOL: bool';
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
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "owner_id" VARCHAR(63) NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_experiments_flag_ke_efbf3d" ON "experiments" ("flag_key");
CREATE INDEX IF NOT EXISTS "idx_experiments_status_2d66b5" ON "experiments" ("status");
COMMENT ON COLUMN "experiments"."status" IS 'DRAFT: draft\nON_REVIEW: on_review\nAPPROVED: approved\nRUNNING: running\nPAUSED: paused\nCOMPLETED: completed\nARCHIVED: archived\nREJECTED: rejected';
CREATE TABLE IF NOT EXISTS "variants" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "value" JSONB NOT NULL,
    "weight" DOUBLE PRECISION NOT NULL,
    "is_control" BOOL NOT NULL,
    "experiment_id" UUID NOT NULL REFERENCES "experiments" ("id") ON DELETE CASCADE
);
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
