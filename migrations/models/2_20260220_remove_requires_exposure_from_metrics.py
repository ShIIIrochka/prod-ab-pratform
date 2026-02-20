from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "metrics" DROP COLUMN IF EXISTS "requires_exposure";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "metrics" ADD "requires_exposure" BOOL NOT NULL DEFAULT False;
        COMMENT ON COLUMN "metrics"."requires_exposure" IS 'Whether metric requires exposure event for attribution';"""
