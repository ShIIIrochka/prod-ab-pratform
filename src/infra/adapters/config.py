from __future__ import annotations

import os

from dataclasses import dataclass


@dataclass
class Config:
    debug: bool
    db_uri: str
    jwt_secret_key: str
    jwt_alg: str
    jwt_access_expires: int
    jwt_refresh_expires: int
    redis_url: str
    pending_events_ttl_seconds: int
    max_concurrent_experiments: int
    cooldown_period_days: int
    experiments_before_cooldown: int
    cooldown_experiment_probability: float
    rotation_period_days: int

    @classmethod
    def get_config(cls) -> Config:
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
                pending_events_ttl_seconds=int(
                    os.environ.get("PENDING_EVENTS_TTL", "604800")
                ),  # 7 дней по умолчанию
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
            )
        except KeyError:
            raise RuntimeError("Required variables are not set")
