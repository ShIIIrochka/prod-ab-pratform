from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
)
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import HTTPConnection
from starlette.responses import Response
from starlette.status import HTTP_401_UNAUTHORIZED

from src.application.ports.jwt import JWTPort
from src.domain.value_objects.user_role import UserRole
from src.infra.observability.metrics import (
    http_errors_total,
    http_requests_total,
)


@dataclass(slots=True)
class AuthUser(BaseUser):
    id: str
    role: UserRole

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
            # raise AuthenticationError("Token verification failed.")
            return None
        return AuthCredentials(["authenticated", payload.role]), AuthUser(
            id=payload.user_id, role=UserRole(payload.role)
        )

    @classmethod
    async def auth_required(cls, request: Request):
        if request.user.is_authenticated:
            return
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="User is not authenticated.",
        )


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method
        path = request.url.path

        response = await call_next(request)

        status_code = response.status_code
        status_label = str(status_code)

        http_requests_total.labels(
            method=method,
            path=path,
            status_code=status_label,
        ).inc()

        if status_code >= 500:
            http_errors_total.labels(
                method=method,
                path=path,
                status_code=status_label,
            ).inc()

        return response
