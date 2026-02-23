import os

from dataclasses import dataclass


_DB_MODELS = ["src.infra.adapters.db.models"]
_TORTOISE_MODULES = {"models": _DB_MODELS}


@dataclass
class Config:
    debug: bool
    db_uri: str
    jwt_secret_key: str
    jwt_alg: str
    jwt_access_expires: int
    jwt_refresh_expires: int
    redis_url: str
    rabbitmq_url: str
    pending_events_ttl_seconds: int
    max_concurrent_experiments: int
    cooldown_period_days: int
    experiments_before_cooldown: int
    cooldown_experiment_probability: float
    rotation_period_days: int
    guardrail_check_interval_seconds: int
    notification_task_max_retries: int
    notification_task_retry_backoff_seconds: int

    @classmethod
    def get_config(cls) -> "Config":
        try:
            host = os.environ["DB_HOST"]
            port = os.environ["DB_PORT"]
            user = os.environ["DB_USER"]
            name = os.environ["DB_NAME"]
            password = os.environ["DB_PASSWORD"]
            return cls(
                debug=True,
                db_uri=f"asyncpg://{user}:{password}@{host}:{port}/{name}",
                jwt_secret_key=os.environ["JWT_SECRET"],
                jwt_alg=os.environ["JWT_ALG"],
                jwt_access_expires=int(os.environ["JWT_ACCESS_EXPIRES"]),
                jwt_refresh_expires=int(os.environ["JWT_REFRESH_EXPIRES"]),
                redis_url=os.environ.get(
                    "REDIS_URL", "redis://localhost:6379/0"
                ),
                rabbitmq_url=os.environ.get(
                    "RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"
                ),
                pending_events_ttl_seconds=int(
                    os.environ["PENDING_EVENTS_TTL"]
                ),
                max_concurrent_experiments=int(
                    os.environ["MAX_CONCURRENT_EXPERIMENTS"]
                ),
                cooldown_period_days=int(os.environ["COOLDOWN_DAYS"]),
                experiments_before_cooldown=int(
                    os.environ["EXPERIMENTS_BEFORE_COOLDOWN"]
                ),
                cooldown_experiment_probability=float(
                    os.environ["COOLDOWN_PROBABILITY"]
                ),
                rotation_period_days=int(os.environ["ROTATION_DAYS"]),
                guardrail_check_interval_seconds=int(
                    os.environ["GUARDRAIL_CHECK_INTERVAL_SECONDS"]
                ),
                notification_task_max_retries=int(
                    os.environ["NOTIFICATION_TASK_MAX_RETRIES"]
                ),
                notification_task_retry_backoff_seconds=int(
                    os.environ["NOTIFICATION_TASK_RETRY_BACKOFF_SECONDS"]
                ),
            )
        except KeyError:
            raise RuntimeError("Required variables are not set")
