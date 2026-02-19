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
    "id" SERIAL NOT NULL PRIMARY KEY,
    "experiment_id" VARCHAR(36) NOT NULL,
    "metric_key" VARCHAR(255) NOT NULL,
    "threshold" DOUBLE PRECISION NOT NULL,
    "observation_window_minutes" INT NOT NULL,
    "action" VARCHAR(50) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_guardrail_c_experim_2b0401" ON "guardrail_configs" ("experiment_id");
CREATE INDEX IF NOT EXISTS "idx_guardrail_c_metric__f30d3f" ON "guardrail_configs" ("metric_key");
COMMENT ON COLUMN "guardrail_configs"."id" IS 'Auto-increment ID';
COMMENT ON COLUMN "guardrail_configs"."experiment_id" IS 'Experiment UUID';
COMMENT ON COLUMN "guardrail_configs"."metric_key" IS 'Metric key';
COMMENT ON COLUMN "guardrail_configs"."threshold" IS 'Threshold value for guardrail trigger';
COMMENT ON COLUMN "guardrail_configs"."observation_window_minutes" IS 'Observation window in minutes';
COMMENT ON COLUMN "guardrail_configs"."action" IS 'GuardrailAction enum: pause or rollback_to_control';
CREATE TABLE IF NOT EXISTS "guardrail_triggers" (
    "id" SERIAL NOT NULL PRIMARY KEY,
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
    "requires_exposure" BOOL NOT NULL DEFAULT False,
    "description" TEXT
);
COMMENT ON COLUMN "metrics"."key" IS 'Metric key (primary identifier)';
COMMENT ON COLUMN "metrics"."name" IS 'Human-readable metric name';
COMMENT ON COLUMN "metrics"."calculation_rule" IS 'Metric calculation rule';
COMMENT ON COLUMN "metrics"."requires_exposure" IS 'Whether metric requires exposure event for attribution';
COMMENT ON COLUMN "metrics"."description" IS 'Metric description';
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
    "eJztXW1zm7gW/isaPnVn0s46abLbzJ2dcRLSejexM47TdrbZYWSQbbZYUAFxMt389yuJdx"
    "AEHGNwwpc2lnRAeiQdPefoSPyUlqaGDPtd37KIeQeNS/ZTOgY/JQyXiP4hLrAHJGhZUTZL"
    "cODU4BLQL8pT4dR2CFQdmjGjSYgmachWiW45uolpKnYNgyWaKi2o43mU5GL9h4sUx5wjZ4"
    "EIzfj2D03WsYbukc1+fpPQvYWIvkTYUXSNvc+1EWF//sOKWt+VmY4MLdEgrxxPV5wHi6fd"
    "3AzOznlJVpWpopqGu8RRaevBWZg4LO66uvaOybC8OcKIQAdpsSayFvhwBElea2iCQ1wUNk"
    "OLEjQ0g67BgJL+N3OxyvAB/E3sn/d/SBWgU03MYNexw3D6+ei1KmozT5XYq04/9cdvDo5+"
    "4a00bWdOeCZHRHrkgtCBnijHPAJSNZcM+CyaE3TviNGMiaQgpdUtAaYPVYhlUCQCMxpkAZ"
    "oBShuHbiJ/nbA6L237B5sz0vBzf8zxvOx/5YAuH/yci9HwY1DcpNPBmyjD04vRCQc5AtWh"
    "g9l24NLKwnpGcWHZYmgTgilwNV/yXfDHOuO2fqwlgqA2wsaD39NF2A8u5etJ//Iq0QFn/Y"
    "nMcvYT4Aepb7xRHuEfPgR8GUw+AfYT/D0ayum5EJab/C2xOkHXMRVsrhSoxeZvkBoAk+jW"
    "jJ4qq38ygptURY1Onyc1T4ReoNQzuJ0uIBHjFhNZS9M0MfyX8F4xEJ47C/rz6KAAu0DRHB"
    "2khnSggvZ51uMjWwVn34XqOxpZWVzPTYL0Of4LPXB0B7SeEKtIgKZPD+TwYSFBaB/Aj8Eg"
    "CVKjyUvgKqQK2TlH20sbhRxvzPWvT/tnspQZoRuA8YY+5gUAGJt8CejGVI2OB6cTiY/LKV"
    "S/ryDRlMQAZTnmvplKCctms5b7y3QKxHDOAWDNYJX24T1Dqm7TNuey3GSBQpar+UXrZ7kd"
    "k62byc4MOFe+o4cqC0xcpq4VJoPnJheY/cPDEisMLZW7xPC85EpNzT4XZWH883o0FMMYCq"
    "Qpq6464D9g6LbTal0owo61ttgwSNsAqSHLHpA2DGKL0h0iTPNkYR7gHLtLLJyCXMdloN6+"
    "CUZrRP97u997/9v73w+O3v9Oi/CqhCm/FXTGYDjpTKzOxNqSidUqB0VnYW3BwkqufkSHlc"
    "dfUuqVDL4Cw7SzparZUmIl2IhR39gIfKZNfy1PwPDm4kISTecNIPnZe9Luw5jUVWK/SDO2"
    "vXwXjlOBYR/L3Suy6hErt42Nq8B94CPJ38tHDbcpafFvku1O/0VqgHVEPnlmSiBZoPMY1O"
    "0xyMJfljZlJTvvQYBqalKUhTQltpN4HhyVgPMgbV5FaLKsJJhJ9VEWy6TUTkJZy9DcJafB"
    "htHdER9BgEOhk8AipmVX8U+GAtv3T8aWwqmrG46O7XfstYLVUOL8BrDKIuLoiNe4fT5M6N"
    "D6TF1WaYXOCccVdEW+ahJLb8/3IFkIawzOLPz9qGrXvGYAYXd5DHyJPRDUHWl7gCCmYZFW"
    "ro+Suu3w1xKq7fDXXM3GsgTGd4OUfUKbUEzboxJPU3cfkbr5e0ew6ybYFVn1Rqn00yC2nq"
    "7w/yvgF5TfTU/uYa9XRi32evl6keWljZGoZhkk80McU2JdmKMwzJGgH65OkKZYkMBlJUYm"
    "EG01N2vtjrIPpK2ge1rUJQKFcWKaBoK4sCOS8qmumNIH1NUHVZf18nCfjEYXCbhPBukxfX"
    "N5Io/feAqFFtI9H6i32dwWepVy34v4VdbDX0CwwsIdwdp9gtXFPHVcqzUQFjkDZGpJZ7bZ"
    "kj7L2p0B2UmuEThzBJ6As3H/fHIMePYtHg2Vsfx5IH85BrRaBN3paHWL+1dX49Fn+ewYeE"
    "elkHaLxzfD4WD48RgQF2PaG7f4qn9zzcpY0LVZidPR5dWFPGFJqrm02LYbTWWgDrxnEXWh"
    "e8+S/5RPecHnuBo+lOjmD7md/CETG1E5aO25kWprTZXeM+bJhuPUoKvpiI53ZcaWWSF254"
    "YJc9ATSqdwnDHxdiqdAqTORjcnFzK4Gsung+uBT4xDLzPPTLKysdy/SLvzIaHcg1ZAIa4h"
    "0N759l1WsjPxhCaer6SE4zbfuktKPcuwaxXE9VhwpmEwW4EyaRa64dDfCpvsd5VNucIHdT"
    "adSHkoS0Qro1bl0ELhHVEhW2CCES6VnEIpsXY4hNj7dskhpBLEUFGgIOSteJM7KdmFxrcs"
    "NN61tDU7NinZdWyjHetXPupXc4Urh+3HZXbTA1H7yWgOkcDYeqUR6PERU/k4b8yc9a+FUQ"
    "hSTaIJlvcT/wnnf42RAXNsgLz7aHYHX2HI4zPhyBxcbh13LIWGH17+TDAqRtu3aWjUuR90"
    "TjmaS9C5Aee5G0KZMntFO0Izr7TC9gUa3BPqYkXWMLnyd4b4kWwPFyGqTzvkk0/YYoSeD2"
    "YGboktVMy77hW4xZ6tz0BfThG5xcw7cAwCz0ZlRlKGkOTzkWzkCW+QUvkwfUawO1RfbPF2"
    "MT51OoA7d8JLsDo7d8IL7diQcLYgVumjSx9BMTZOTTzT8/mpsFwhR50HEoxtU5Ht30rKz2"
    "vG/P3Vjmfmbo8LXTiCnXG/42sgsVKfDqa3OqbqmrUVeBFV29ooLzicWXwTSMHZzCduAtly"
    "kJMUheeBIF6t+XOF6217bWC/a3O4XvLKAL8yrdj3chZUjS9MQzBeC4I8ElKNB3dIk6A6gF"
    "sgYGYSEOpf2jn6fO45VhuP/zCnNiJ33I+krGhD6TK51LHrIIHrKVcDFz9kezFL4s4YRbUD"
    "Xu2AjkGsgg1ENOWEMRWc+csLXdr2XoUUMo++t8vrH/BjwXmADnNBBMU6uuVFne8LIZt4M/"
    "9pVpcoWJLW+WqlIV7nv92zaV4s09tyDGRH7V4ZtXvaGdYxuzYxu47DdRyu43C1crgU5i40"
    "8vaDig4BpASbVyR9XiPgrRm+mQgdQCkXYC5fYM5aZScm6F0G+Sdu/knJtsrdLU2Ce4nAao"
    "FwzExfQRuEVS85/l+KS9zb62iJ+eRxmVyjKZ5daCp5c62Lz1iTSII3FiXqkDwAXaN0XafN"
    "IL80zC7zDaQdPYwqfXLpPHjL9Ah7drA+BLWrvgSXW4OLFuHMKqxCQ3W92LPKp8ZEsk1D7g"
    "/xWNVAULX2BRO8zMsqpC8Lrk2D8R7UEgS1BPxWK+5Ij11/9uwu2uBhqJcQQhNMhVSl2jEL"
    "WsJGomB2ARdJRLrnMxF2l3nL7g7JXxk36SbcbpTopj5sUOCGXVJLoZL7NRDYRTxrcQta0L"
    "ZXJqk0JOMyu3l2pxYoiSkiY+VClQPZLQYps0tAfPdGyjdydjkYHgOoLXV8i+WvV/KYGrDD"
    "CQtUjvYvWLiyf4PIOLxBhKaxa0ZYSuzxFTunt1+ib3r7uV3DslKOq+DMz5yYruDq5PxQ5q"
    "xkdxdAd3g3fyC/Wg9UdrLZylynVoPAQOrO160LR9XzdW2FI3WH3/qA7PQHf2s9Zpc4fSiw"
    "ldKnE/PNpfhpyPZYTN1ti2klX+K2xWbdsi/AXOo+LFsXcVwhfb4QfeQsf1s5Eml8Q3kTsG"
    "5io1i34yEDFRzTScEteqRrg3ODzuVWfNO1Xeiu/13Nhr8N2SL+t1fp45AlPmzYuL3Rovs8"
    "6uTWfdpN6kISsGo/p5BPw6hMa9h0F/T9dNB37tXB+fw5/+7g1+woZ1OjAoh+8d0EsFcqBK"
    "RXEALSE4SAUKYmXD+LLrQNRTpLJGuJNLq7/fh/DgCdzw=="
)
