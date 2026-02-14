from pydantic import BaseModel, Field

from domain.aggregates.user import User


class ApprovalGroupResponse(BaseModel):
    """Approval group configuration for EXPERIMENTER role."""

    experimenter_id: str = Field(..., description="Experimenter UUID")
    approver_ids: list[str] = Field(..., description="List of approver UUIDs")
    min_approvals_required: int = Field(
        ..., description="Minimum number of approvals required"
    )


class UserResponse(BaseModel):
    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    approval_group: ApprovalGroupResponse | None = Field(
        default=None, description="Approval group (for EXPERIMENTER role)"
    )

    @classmethod
    def from_domain(cls, user: User) -> UserResponse:
        approval_group = ApprovalGroupResponse(
            experimenter_id=user.approval_group.experimenter_id,
            approver_ids=user.approval_group.approver_ids,
            min_approvals_required=user.approval_group.min_approvals_required,
        )
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            approval_group=approval_group,
        )
