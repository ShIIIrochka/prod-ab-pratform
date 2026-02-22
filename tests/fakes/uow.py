"""Fake UnitOfWork — no-op context manager for tests."""

from __future__ import annotations

from src.application.ports.uow import UnitOfWorkPort


class FakeUnitOfWork(UnitOfWorkPort):
    """In-memory no-op UoW — transactions are not actually used in unit tests."""

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
