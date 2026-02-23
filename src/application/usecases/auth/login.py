from __future__ import annotations

from src.application.dto.auth import (
    LoginRequest,
)
from src.application.ports.jwt import JWTPort
from src.application.ports.password_hasher import PasswordHasherPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.domain.exceptions.auth import CouldNotAuthorizeError
from src.domain.value_objects.jwt import JWTPayload, Tokens


class LoginUseCase:
    def __init__(
        self,
        users_repository: UsersRepositoryPort,
        password_hasher: PasswordHasherPort,
        jwt_adapter: JWTPort,
    ) -> None:
        self._users_repository = users_repository
        self._password_hasher = password_hasher
        self._jwt_adapter = jwt_adapter

    async def execute(self, data: LoginRequest) -> Tokens:
        user = await self._users_repository.get_by_email(data.email)
        if not user or not self._password_hasher.verify(
            data.password, user.password
        ):
            raise CouldNotAuthorizeError

        payload = JWTPayload.make_payload(role=user.role, user_id=user.id)

        access_token = await self._jwt_adapter.create("access", payload)
        refresh_token = await self._jwt_adapter.create("refresh", payload)
        return Tokens(access_token=access_token, refresh_token=refresh_token)
