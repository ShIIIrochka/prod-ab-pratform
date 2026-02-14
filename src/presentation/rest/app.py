from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from infra.adapters.config import Config
from infra.adapters.db.db import Database
from presentation.rest.exception_handlers import setup_exc_handlers
from presentation.rest.routes import auth, decide


@asynccontextmanager
async def lifespan(_: FastAPI):
    config = Config.get_config()
    db = Database(
        db_uri=config.db_uri,
        modules={"models": ["src.infra.adapters.db.models"]},
    )
    await db.connect()

    yield

    await db.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title="A/B Platform",
        description="A/B testing platform backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    @app.get("/ready")
    async def ready():
        return JSONResponse({"status": "ready"})

    setup_exc_handlers(app)
    app.include_router(auth.router)
    app.include_router(decide.router)

    return app
