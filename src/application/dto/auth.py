from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from src.domain.value_objects.user_role import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    role: UserRole = Field(
        default=UserRole.VIEWER, description="User role (default: VIEWER)"
    )
    approver_ids: list[str] | None = Field(
        default=None,
        description="Список id апруверов для роли EXPERIMENTER (опционально)",
    )
    min_approvals_required: int | None = Field(
        default=None,
        description="Минимальное число одобрений для EXPERIMENTER (опционально)",
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")

    class Config:
        from_attributes = True
