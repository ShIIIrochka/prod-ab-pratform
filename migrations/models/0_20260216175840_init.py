from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
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
    "completion" JSONB,
    "rollback_to_control_active" BOOL NOT NULL DEFAULT False,
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
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "value" JSONB NOT NULL,
    "weight" DOUBLE PRECISION NOT NULL,
    "is_control" BOOL NOT NULL,
    "experiment_id" UUID NOT NULL REFERENCES "experiments" ("id") ON DELETE CASCADE
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
    "CkZiJpJrLTb7cf/we+WKQi"
)
