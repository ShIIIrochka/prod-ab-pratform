from __future__ import annotations

import asyncio
import os

from collections.abc import AsyncGenerator, Generator

import asyncpg
import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient


_TEST_DB_NAME = "test"
_REDIS_TEST_DB_INDEX = 15


def _get_pg_params() -> dict[str, str]:
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "postgres"),
    }


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def set_env() -> Generator[None]:
    """Configure environment variables pointing to external Postgres and Redis."""
    pg = _get_pg_params()
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = os.environ.get("REDIS_PORT", "6379")
    redis_url = f"redis://{redis_host}:{redis_port}/{_REDIS_TEST_DB_INDEX}"

    rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
    rabbitmq_port = os.environ.get("RABBITMQ_PORT", "5672")
    rabbitmq_url = f"amqp://guest:guest@{rabbitmq_host}:{rabbitmq_port}//"

    os.environ.update(
        {
            "DB_HOST": pg["host"],
            "DB_PORT": pg["port"],
            "DB_USER": pg["user"],
            "DB_PASSWORD": pg["password"],
            "DB_NAME": _TEST_DB_NAME,
            "JWT_SECRET": "test-secret-key-for-e2e-tests",
            "JWT_ALG": "HS256",
            "JWT_ACCESS_EXPIRES": "3600",
            "JWT_REFRESH_EXPIRES": "86400",
            "REDIS_URL": redis_url,
            "RABBITMQ_URL": rabbitmq_url,
            "PENDING_EVENTS_TTL": "604800",
            "MAX_CONCURRENT_EXPERIMENTS": "5",
            "COOLDOWN_DAYS": "7",
            "EXPERIMENTS_BEFORE_COOLDOWN": "3",
            "COOLDOWN_PROBABILITY": "0.3",
            "ROTATION_DAYS": "30",
            "GUARDRAIL_CHECK_INTERVAL_SECONDS": "60",
            "NOTIFICATION_TASK_MAX_RETRIES": "3",
            "NOTIFICATION_TASK_RETRY_BACKOFF_SECONDS": "60",
        }
    )
    yield


@pytest_asyncio.fixture(scope="session")
async def ensure_test_db(set_env) -> None:
    """Drop and recreate the test database to ensure a clean schema each run.

    Connects to the 'postgres' maintenance database to issue DROP/CREATE.
    Requires CREATEDB privilege for DB_USER.
    """
    pg = _get_pg_params()
    conn = await asyncpg.connect(
        host=pg["host"],
        port=int(pg["port"]),
        user=pg["user"],
        password=pg["password"],
        database="postgres",
    )
    try:
        # Terminate any existing connections so the DROP succeeds
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            _TEST_DB_NAME,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
        await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session")
async def flush_redis(set_env) -> None:
    """Flush the dedicated Redis test DB before the test session."""
    from redis.asyncio import Redis

    redis_url = os.environ["REDIS_URL"]
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        await redis.flushdb()
    finally:
        await redis.aclose()


# Cached admin token so we only register+login once per session (function-scoped
# client gets a new app each test, but DB is shared so the user persists).
_admin_token_cache: dict[str, str] = {}


@pytest_asyncio.fixture
async def app(ensure_test_db, flush_redis):
    """New FastAPI app per test so each test has its own lifespan and worker teardown."""
    from src.presentation.rest.app import create_app

    return create_app()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient]:
    """Per-test client and lifespan: workers start/stop with the test, no shared state."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        async with app.router.lifespan_context(app):
            yield ac


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    if _admin_token_cache:
        return _admin_token_cache["token"]
    reg = await client.post(
        "/auth/register",
        json={
            "email": "e2e-admin@example.com",
            "password": "e2e_admin_pass",
            "role": "admin",
        },
    )
    assert reg.status_code in (201, 400), (
        f"Unexpected register status: {reg.text}"
    )
    login = await client.post(
        "/auth/login",
        json={
            "email": "e2e-admin@example.com",
            "password": "e2e_admin_pass",
        },
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    _admin_token_cache["token"] = token
    return token


@pytest.fixture
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def create_subject_users(client: AsyncClient) -> None:
    from src.infra.adapters.db.models.user import UserModel

    subject_ids = [
        "e2e-user-alice",
        "e2e-user-bob",
        "alice-diff",
        "bob-diff",
        "dedup-test-user",
        "validation-user",
        "anon-user",
    ]
    for sid in subject_ids:
        await UserModel.get_or_create(
            id=sid,
            defaults={
                "email": f"{sid}@e2e.test",
                "password": "hashed_stub",
                "role": "viewer",
            },
        )
