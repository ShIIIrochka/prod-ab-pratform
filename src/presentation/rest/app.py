from __future__ import annotations

import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware

from src.application.ports.jwt import JWTPort
from src.infra.adapters.config import Config
from src.infra.adapters.db.db import Database
from src.infra.workers.guardrail_checker_worker import GuardrailCheckerWorker
from src.infra.workers.pending_events_ttl_listener import (
    PendingEventsTTLListener,
)
from src.presentation.rest.dependencies import container
from src.presentation.rest.exception_handlers import setup_exc_handlers
from src.presentation.rest.middlewares import JWTBackend
from src.presentation.rest.routes import (
    auth,
    decide,
    event_types,
    events,
    experiments,
    feature_flags,
    metrics,
    reports,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    config: Config = container.resolve(Config)
    db = Database(
        db_uri=config.db_uri,
        modules={"models": ["src.infra.adapters.db.models"]},
    )
    await db.connect()

    ttl_listener: PendingEventsTTLListener = container.resolve(
        PendingEventsTTLListener
    )
    ttl_task = asyncio.create_task(ttl_listener.start())

    guardrail_worker: GuardrailCheckerWorker = container.resolve(
        GuardrailCheckerWorker
    )
    guardrail_task = asyncio.create_task(guardrail_worker.start())

    yield

    guardrail_task.cancel()
    try:
        await guardrail_task
    except asyncio.CancelledError:
        pass

    ttl_task.cancel()
    try:
        await ttl_task
    except asyncio.CancelledError:
        pass
    await db.disconnect()

    redis: Redis = container.resolve(Redis)
    await redis.aclose()


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
    app.include_router(events.router)
    app.include_router(event_types.router)
    app.include_router(metrics.router)
    app.include_router(reports.router)

    return app
