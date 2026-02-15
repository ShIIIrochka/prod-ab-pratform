from __future__ import annotations

from pydantic import BaseModel, Field


class ApprovalGroupResponse(BaseModel):
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

    class Config:
        from_attributes = True
