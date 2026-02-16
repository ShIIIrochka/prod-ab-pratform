from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.value_objects.approval import Approval


class ApprovalModel(Model):
    id = fields.UUIDField(pk=True)
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel",
        related_name="approval_records",
        on_delete=OnDelete.CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.UserModel",
        related_name="approvals_given",
        on_delete=OnDelete.RESTRICT,
        to_field="id",
    )
    comment = fields.TextField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "approvals"
        indexes = [
            ("experiment_id", "user_id"),
        ]

    def to_domain(self) -> Approval:
        return Approval(
            user_id=str(self.user_id),
            comment=self.comment,
            timestamp=self.timestamp,
        )
