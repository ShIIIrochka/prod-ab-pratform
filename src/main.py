from __future__ import annotations

from src.infra.adapters.config import Config
from src.infra.aerich_config import get_aerich_config
from src.presentation.rest.app import create_app
from src.presentation.rest.dependencies import container


config: Config = container.resolve(Config)
AERICH_CONFIG = get_aerich_config(config.db_uri)
app = create_app()

if __name__ == "__main__":
    import asyncio

    from granian.server.embed import Server

    server = Server(target=app, interface="asgi")
    asyncio.run(server.serve())
