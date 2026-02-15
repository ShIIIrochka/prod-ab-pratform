from __future__ import annotations

from dataclasses import asdict

from tortoise import fields
from tortoise.models import Model

from src.domain.aggregates.user import ApprovalGroup, User
from src.domain.value_objects.user_role import UserRole


class UserModel(Model):
    id = fields.CharField(pk=True, max_length=63)
    email = fields.CharField(
        max_length=255,
        unique=True,
    )
    password = fields.CharField(max_length=255)
    role = fields.CharEnumField(UserRole, default=UserRole.VIEWER)

    approval_group = fields.JSONField(
        null=True,
    )

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def to_domain(self) -> User:
        approval_group = None
        if self.approval_group:
            approval_group = ApprovalGroup(
                experimenter_id=self.approval_group.get("experimenter_id"),
                approver_ids=self.approval_group.get("approver_ids"),
                min_approvals_required=self.approval_group.get(
                    "min_approvals_required"
                ),
            )
        return User(
            id=self.id,
            email=self.email,
            role=self.role,
            password=self.password,
            approval_group=approval_group,
        )

    @classmethod
    def from_domain(cls, user: User) -> UserModel:
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            password=user.password,
            approval_group=asdict(user.approval_group)
            if user.approval_group
            else None,
        )
