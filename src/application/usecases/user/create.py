from __future__ import annotations

from application.dto.auth import RegisterRequest
from application.ports.password_hasher import PasswordHasherPort
from application.ports.users_repository import UsersRepositoryPort
from domain.aggregates.user import User
from domain.exceptions.users import UserAlreadyExistsException


class CreateUserUseCase:
    def __init__(
        self,
        users_repository: UsersRepositoryPort,
        password_hasher: PasswordHasherPort,
    ) -> None:
        self._users_repository = users_repository
        self._password_hasher = password_hasher

    async def execute(self, data: RegisterRequest) -> User:
        if await self._users_repository.get_by_email(data.email):
            raise UserAlreadyExistsException

        password_hash = self._password_hasher.hash(data.password)

        user = User(
            email=data.email,
            role=data.role,
            password=password_hash,
            approval_group=None,
        )

        await self._users_repository.save(user)
        return user
