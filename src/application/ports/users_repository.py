from __future__ import annotations

from abc import ABC, abstractmethod

from domain.aggregates.user import User


class UsersRepositoryPort(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> None:
        raise NotImplementedError
