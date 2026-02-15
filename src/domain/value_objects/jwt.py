from __future__ import annotations

from dataclasses import dataclass

from src.domain.value_objects.user_role import UserRole


@dataclass(frozen=True)
class JWTPayload:
    user_id: str
    role: str

    @classmethod
    def make_payload(cls, role: UserRole, user_id: str) -> JWTPayload:
        return cls(
            user_id=str(user_id),
            role=str(role.value),
        )


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str
