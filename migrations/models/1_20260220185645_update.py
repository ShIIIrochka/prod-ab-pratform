from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "metrics" ADD "aggregation_unit" VARCHAR(10) NOT NULL DEFAULT 'event';
        COMMENT ON COLUMN "metrics"."aggregation_unit" IS 'Aggregation unit: event or user';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "metrics" DROP COLUMN "aggregation_unit";"""


MODELS_STATE = (
    "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"
    "pN5QpiZcP4suEg5FOk8k64k0urv9+H/schgR"
)
