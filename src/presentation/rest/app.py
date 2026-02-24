import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from redis.asyncio import Redis
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware

from src.application.ports.jwt import JWTPort
from src.application.ports.password_hasher import PasswordHasherPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.domain.aggregates.user import User
from src.domain.value_objects.user_role import UserRole
from src.infra.adapters.config import Config
from src.infra.adapters.db.db import Database
from src.infra.adapters.opensearch.opensearch import OpenSearch
from src.infra.workers.guardrail_checker_worker import GuardrailCheckerWorker
from src.infra.workers.pending_events_ttl_listener import (
    PendingEventsTTLListener,
)
from src.presentation.rest.dependencies import Container, container
from src.presentation.rest.exception_handlers import setup_exc_handlers
from src.presentation.rest.middlewares import JWTBackend, MetricsMiddleware
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
from src.presentation.rest.routes.experiment_versions import (
    router as experiment_versions_router,
)
from src.presentation.rest.routes.learnings import (
    router as learnings_router,
)
from src.presentation.rest.routes.notifications import (
    router as notifications_router,
)


async def _ensure_admin_user() -> None:
    config: Config = container.resolve(Config)
    if not config.admin_email or not config.admin_password:
        return

    users: UsersRepositoryPort = container.resolve(UsersRepositoryPort)
    hasher: PasswordHasherPort = container.resolve(PasswordHasherPort)
    existing = await users.get_by_email(config.admin_email)
    if existing is not None:
        return
    user = User(
        email=config.admin_email,
        role=UserRole.ADMIN,
        password=hasher.hash(config.admin_password),
        approval_group=None,
    )
    await users.save(user)


@asynccontextmanager
async def lifespan(_: FastAPI):
    config: Config = container.resolve(Config)
    db = Database(
        db_uri=config.db_uri,
        modules={"models": ["src.infra.adapters.db.models"]},
    )
    await db.connect()

    await _ensure_admin_user()

    opensearch: OpenSearch = container.resolve(OpenSearch)
    await opensearch.connect()

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

    await opensearch.disconnect()
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
            ),
            Middleware(MetricsMiddleware),
        ],
    )

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    @app.get("/ready")
    async def ready(container: Container):
        opensearch_ok = True
        # opensearch: OpenSearch = container.resolve(OpenSearch)
        # try:
        # await opensearch.ping()
        # except Exception:
        # opensearch_ok = False

        if not opensearch_ok:
            return JSONResponse(
                {
                    "status": "not_ready",
                    "opensearch_ok": opensearch_ok,
                },
                status_code=503,
            )

        return JSONResponse({"status": "ready"})

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> PlainTextResponse:
        data = generate_latest()
        return PlainTextResponse(
            content=data.decode("utf-8"),
            media_type=CONTENT_TYPE_LATEST,
        )

    setup_exc_handlers(app)
    app.include_router(auth.router)
    app.include_router(decide.router)
    app.include_router(feature_flags.router)
    app.include_router(experiments.router)
    app.include_router(events.router)
    app.include_router(event_types.router)
    app.include_router(metrics.router)
    app.include_router(reports.router)
    app.include_router(notifications_router)
    app.include_router(experiment_versions_router)
    app.include_router(learnings_router)

    return app
