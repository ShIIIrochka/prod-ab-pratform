from __future__ import annotations

from application.dto.user import UserResponse
from application.ports.users_repository import UsersRepositoryPort
from domain.aggregates.user import User
from domain.exceptions.users import UserNotFoundError


class GetUserByIdUseCase:
    def __init__(
        self,
        users_repository: UsersRepositoryPort,
    ) -> None:
        self._users_repository = users_repository

    async def execute(self, user_id: str) -> UserResponse:
        user: User = await self._users_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError
        return UserResponse.from_domain(user)
