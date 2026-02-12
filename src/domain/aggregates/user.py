from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.aggregates import BaseEntity
from domain.value_objects.user_role import UserRole


@dataclass
class ApprovalGroup:
    experimenter_id: UUID
    approver_ids: list[UUID]
    min_approvals_required: int

    def __post_init__(self) -> None:
        if self.min_approvals_required <= 0:
            msg = (
                f"Min approvals required must be positive, "
                f"got {self.min_approvals_required}"
            )
            raise ValueError(msg)
        if self.min_approvals_required > len(self.approver_ids):
            msg = (
                f"Min approvals required ({self.min_approvals_required}) "
                f"cannot exceed number of approvers ({len(self.approver_ids)})"
            )
            raise ValueError(msg)


@dataclass
class User(BaseEntity):
    email: str
    role: UserRole
    approval_group: ApprovalGroup | None = None

    def set_approval_group(self, group: ApprovalGroup) -> None:
        if self.role != UserRole.EXPERIMENTER:
            msg = f"Approval group can only be set for EXPERIMENTER, got {self.role}"
            raise ValueError(msg)
        self.approval_group = group

    def can_approve_experiments(self) -> bool:
        return self.role in (UserRole.APPROVER, UserRole.ADMIN)

    def can_create_experiments(self) -> bool:
        return self.role == UserRole.EXPERIMENTER
