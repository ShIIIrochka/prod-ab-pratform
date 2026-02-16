from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware

from src.application.ports.jwt import JWTPort
from src.infra.adapters.config import Config
from src.infra.adapters.db.db import Database
from src.presentation.rest.dependencies import container
from src.presentation.rest.exception_handlers import setup_exc_handlers
from src.presentation.rest.middlewares import JWTBackend
from src.presentation.rest.routes import (
    auth,
    decide,
    experiments,
    feature_flags,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    config: Config = container.resolve(Config)
    db = Database(
        db_uri=config.db_uri,
        modules={"models": ["src.infra.adapters.db.models"]},
    )
    await db.connect()

    yield

    await db.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        debug=True,
        title="A/B Platform",
        description="A/B testing platform backend",
        version="0.1.0",
        lifespan=lifespan,
        middleware=[
            Middleware(
                AuthenticationMiddleware,
                backend=JWTBackend(jwt_adapter=container.resolve(JWTPort)),
            )
        ],
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
    app.include_router(feature_flags.router)
    app.include_router(experiments.router)

    return app
