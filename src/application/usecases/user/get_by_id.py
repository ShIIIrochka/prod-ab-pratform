from __future__ import annotations

from src.application.ports.users_repository import UsersRepositoryPort
from src.domain.aggregates.user import User
from src.domain.exceptions.users import UserNotFoundError


class GetUserByIdUseCase:
    def __init__(
        self,
        users_repository: UsersRepositoryPort,
    ) -> None:
        self._users_repository = users_repository

    async def execute(self, user_id: str) -> User:
        user: User | None = await self._users_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError
        return user
