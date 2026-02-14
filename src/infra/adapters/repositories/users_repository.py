from __future__ import annotations

from dataclasses import asdict

from application.ports.users_repository import UsersRepositoryPort
from domain.aggregates.user import User
from infra.adapters.db.models.user import UserModel


class UserRepository(UsersRepositoryPort):
    async def get_by_email(self, email: str) -> User | None:
        model = await UserModel.get_or_none(email=email)
        if model is None:
            return None
        return model.to_domain()

    async def get_by_id(self, user_id: str) -> User | None:
        model = await UserModel.get_or_none(id=user_id)
        if model is None:
            return None
        return model.to_domain()

    async def save(self, user: User) -> None:
        model = await UserModel.get_or_none(email=user.email)
        data = asdict(user)
        if model:
            await UserModel.filter(id=user.id).update(**data)
        else:
            await UserModel.create(**data)
        return None
