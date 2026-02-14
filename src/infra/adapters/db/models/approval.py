from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class ApprovalModel(Model):
    """Tortoise модель для одобрений эксперимента.

    Соответствует domain.value_objects.approval.Approval
    """

    id = fields.IntField(pk=True, description="Auto-increment ID")
    experiment_id = fields.CharField(
        max_length=36, index=True, description="Experiment UUID"
    )
    user_id = fields.CharField(max_length=36, description="Approver User UUID")
    comment = fields.TextField(
        null=True, description="Optional approval comment"
    )
    timestamp = fields.DatetimeField(description="Approval timestamp")

    class Meta:
        table = "approvals"
        indexes = [
            ("experiment_id", "user_id"),
        ]
