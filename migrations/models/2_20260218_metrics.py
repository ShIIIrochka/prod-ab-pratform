from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "metrics" (
            "key" VARCHAR(255) NOT NULL PRIMARY KEY,
            "name" VARCHAR(500) NOT NULL,
            "calculation_rule" TEXT NOT NULL,
            "requires_exposure" BOOL NOT NULL DEFAULT False,
            "description" TEXT
        );
        COMMENT ON COLUMN "metrics"."calculation_rule" IS 'Metric calculation rule';
        COMMENT ON COLUMN "metrics"."requires_exposure" IS 'Whether metric requires exposure event for attribution';

        ALTER TABLE "experiments"
            ADD COLUMN IF NOT EXISTS "target_metric_key" VARCHAR(255),
            ADD COLUMN IF NOT EXISTS "metric_keys" JSONB NOT NULL DEFAULT '[]'::jsonb;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "experiments"
            DROP COLUMN IF EXISTS "target_metric_key",
            DROP COLUMN IF EXISTS "metric_keys";
        DROP TABLE IF EXISTS "metrics";
    """
