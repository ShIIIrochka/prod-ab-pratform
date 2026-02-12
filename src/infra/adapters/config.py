from __future__ import annotations

import os

from dataclasses import dataclass


@dataclass
class Config:
    debug: bool
    db_uri: str

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
            )
        except KeyError:
            raise RuntimeError("Required variables are not set")
