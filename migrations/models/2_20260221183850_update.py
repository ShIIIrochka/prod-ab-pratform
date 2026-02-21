from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "variants" DROP CONSTRAINT IF EXISTS "variants_name_key";
        DROP INDEX IF EXISTS "uid_variants_name_6cc200";
        ALTER TABLE "metrics" DROP COLUMN "requires_exposure";
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_variants_experim_cbfe81" ON "variants" ("experiment_id", "name");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_variants_experim_cbfe81";
        ALTER TABLE "metrics" ADD "requires_exposure" BOOL NOT NULL DEFAULT False;
        COMMENT ON COLUMN "metrics"."requires_exposure" IS 'Whether metric requires exposure event for attribution';
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_variants_name_6cc200" ON "variants" ("name");"""


MODELS_STATE = (
    "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"
    "rvfj/wGuaJiM"
)
