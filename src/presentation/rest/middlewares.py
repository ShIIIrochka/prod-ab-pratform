from typing import Any

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection

from application.ports.jwt import JWTPort


class Payload(BaseUser):
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    @property
    def is_authenticated(self) -> bool:
        return True


class JWTBackend(AuthenticationBackend):
    def __init__(
        self,
        jwt_adapter: JWTPort,
        cookie_name: str | None = None,
        header_name: str | None = "Authorization",
    ) -> None:
        self._jwt = jwt_adapter
        self.cookie_name = cookie_name
        self.header_name = header_name

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        token = None

        if self.cookie_name:
            token = conn.cookies.get(self.cookie_name)

        if not token and self.header_name:
            header = conn.headers.get(self.header_name)
            if header and header.startswith("Bearer "):
                token = header.split("Bearer ")[1]

        if not token:
            return None

        try:
            payload = await self._jwt.verify(token=token)
        except Exception:
            raise AuthenticationError("Token verification failed.")
        return AuthCredentials(["authenticated", payload.role]), Payload(
            payload=payload.__dict__
        )
