from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from domain.value_objects.jwt import Tokens
from domain.value_objects.user_role import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    role: UserRole = Field(
        default=UserRole.VIEWER, description="User role (default: VIEWER)"
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")

    @classmethod
    def from_domain(cls, tokens: Tokens) -> TokenResponse:
        return cls(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
