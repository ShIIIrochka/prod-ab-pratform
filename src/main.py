from __future__ import annotations

from infra.adapters.config import Config
from infra.aerch_config import get_aerich_config
from presentation.rest.app import create_app
from presentation.rest.dependencies import container


config: Config = container.resolve(Config)
AERICH_CONFIG = get_aerich_config(config.db_uri)
app = create_app()

if __name__ == "__main__":
    import asyncio

    from granian.server import Server

    server = Server(target=app, interface="asgi", port=8000)
    asyncio.run(server.serve())
