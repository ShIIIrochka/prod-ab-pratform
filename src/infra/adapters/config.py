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
            )
        except KeyError:
            raise RuntimeError("Required variables are not set")
