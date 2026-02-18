from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.aggregates import BaseEntity
from src.domain.aggregates.user import User
from src.domain.entities.variant import Variant
from src.domain.exceptions.experiment import CannotReviewExperimentError
from src.domain.value_objects.approval import Approval
from src.domain.value_objects.experiment_completion import (
    ExperimentCompletion,
    ExperimentOutcome,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule
from src.domain.value_objects.user_role import UserRole


@dataclass
class Experiment(BaseEntity):
    flag_key: str
    name: str
    status: ExperimentStatus
    version: int
    audience_fraction: float
    variants: list[Variant]
    targeting_rule: TargetingRule | None
    owner_id: str
    target_metric_key: str | None = None
    metric_keys: list[str] = field(default_factory=list)
    approvals: list[Approval] = field(default_factory=list)
    completion: ExperimentCompletion | None = None
    rollback_to_control_active: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.audience_fraction <= 0 or self.audience_fraction > 1:
            msg = (
                f"Audience fraction must be between 0 and 1, "
                f"got {self.audience_fraction}"
            )
            raise ValueError(msg)

        # Валидация вариантов
        control_count = sum(1 for v in self.variants if v.is_control)
        if control_count != 1:
            msg = f"Experiment must have exactly one control variant, got {control_count}"
            raise ValueError(msg)

        total_weight = sum(v.weight for v in self.variants)
        if (
            abs(total_weight - self.audience_fraction) > 0.0001
        ):  # float comparison
            msg = (
                f"Sum of variant weights ({total_weight}) must equal "
                f"audience fraction ({self.audience_fraction})"
            )
            raise ValueError(msg)

    def can_be_edited(self) -> bool:
        return self.status.can_be_edited()

    def can_be_launched(self, owner: User, approver: User) -> bool:
        if not self.status.can_be_launched():
            return False
        if not owner.approval_group:
            # Если группа не задана, одобрение от админа достаточно
            min_approvals = 1 if approver.role == UserRole.ADMIN else None
        else:
            min_approvals = owner.approval_group.min_approvals_required
        if not min_approvals or len(self.approvals) < min_approvals:
            return False
        return True

    def can_be_reviewed(self, owner: User, user: User) -> bool:
        """Проверяет, может ли пользователь ревьюить этот эксперимент."""
        if user.role == UserRole.ADMIN:
            return True
        elif user.role == UserRole.APPROVER:
            if not owner.approval_group:
                return False
            return user.id in owner.approval_group.approver_ids
        return False

    def send_to_review(self) -> None:
        if self.status != ExperimentStatus.DRAFT:
            msg = f"Cannot send to review from status {self.status}"
            raise ValueError(msg)
        self.status = ExperimentStatus.ON_REVIEW
        self.updated_at = datetime.utcnow()

    def request_changes(
        self, owner: User, requesting_user: User, comment: str | None = None
    ) -> None:
        if self.status != ExperimentStatus.ON_REVIEW:
            msg = f"Cannot request changes when status is {self.status}"
            raise ValueError(msg)
        if not self.can_be_reviewed(owner, requesting_user):
            raise CannotReviewExperimentError
        self.status = ExperimentStatus.DRAFT
        self.approvals.clear()
        self.updated_at = datetime.utcnow()

    def reject(
        self, owner: User, rejecting_user: User, comment: str | None = None
    ) -> None:
        if self.status != ExperimentStatus.ON_REVIEW:
            msg = f"Cannot add approval when status is {self.status}"
            raise ValueError(msg)
        if not self.can_be_reviewed(owner, rejecting_user):
            raise CannotReviewExperimentError
        self.status = ExperimentStatus.REJECTED
        self.approvals.clear()
        self.updated_at = datetime.utcnow()

    def approve(
        self, owner: User, approving_user: User, comment: str | None = None
    ) -> None:
        if any(a.user_id == approving_user.id for a in self.approvals):
            raise ValueError("User has already approved this experiment")

        if self.status != ExperimentStatus.ON_REVIEW:
            msg = f"Cannot add approval when status is {self.status}"
            raise ValueError(msg)
        if not self.can_be_reviewed(owner, approving_user):
            raise CannotReviewExperimentError

        approval = Approval(
            user_id=approving_user.id,
            comment=comment,
            timestamp=datetime.utcnow(),
        )
        self.approvals.append(approval)

        approve_count = len(self.approvals)
        # Определяем минимальный порог одобрений
        if not owner.approval_group:
            # Если группа не задана, одобрение от админа достаточно
            min_approvals = 1 if approving_user.role == UserRole.ADMIN else None
        else:
            min_approvals = owner.approval_group.min_approvals_required

        if min_approvals and approve_count >= min_approvals:
            self.status = ExperimentStatus.APPROVED
        self.updated_at = datetime.utcnow()

    def launch(self, owner: User, user: User) -> None:
        if not self.can_be_launched(owner, user):
            msg = f"Cannot launch experiment in status {self.status}"
            raise ValueError(msg)
        self.status = ExperimentStatus.RUNNING
        self.updated_at = datetime.utcnow()

    def pause(self) -> None:
        if self.status != ExperimentStatus.RUNNING:
            msg = f"Cannot pause experiment in status {self.status}"
            raise ValueError(msg)
        self.status = ExperimentStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def complete(
        self,
        outcome: ExperimentOutcome,
        comment: str,
        completed_by: UUID,
        winner_variant_id: str | None,
    ) -> None:
        if self.status not in (
            ExperimentStatus.RUNNING,
            ExperimentStatus.PAUSED,
        ):
            msg = f"Cannot complete experiment in status {self.status}"
            raise ValueError(msg)

        if not comment or not comment.strip():
            msg = "Completion comment is required and cannot be empty"
            raise ValueError(msg)

        if (
            outcome == ExperimentOutcome.ROLLOUT_WINNER
            and not winner_variant_id
        ):
            msg = "Winner variant ID is required for ROLLOUT_WINNER outcome"
            raise ValueError(msg)

        # Проверяем, что winner_variant_id существует в вариантах
        variant_names = [v.name for v in self.variants]
        if winner_variant_id not in variant_names:
            msg = (
                f"Winner variant '{winner_variant_id}' "
                f"not found in experiment variants"
            )
            raise ValueError(msg)

        self.completion = ExperimentCompletion(
            outcome=outcome,
            winner_variant_id=winner_variant_id,
            comment=comment,
            completed_at=datetime.utcnow(),
            completed_by=completed_by,
        )
        self.status = ExperimentStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        return self.status.is_active()

    def activate_rollback_to_control(self) -> None:
        """Вызывается при срабатывании guardrail с действием ROLLBACK_TO_CONTROL."""
        if self.status != ExperimentStatus.RUNNING:
            msg = (
                f"Rollback to control only applies to running experiments, "
                f"current status: {self.status}"
            )
            raise ValueError(msg)
        self.rollback_to_control_active = True
        self.updated_at = datetime.utcnow()

    def clear_rollback_to_control(self) -> None:
        """Снимает режим отката к контролю (например при ручном возобновлении)."""
        self.rollback_to_control_active = False
        self.updated_at = datetime.utcnow()

    def get_control_variant(self) -> Variant:
        """Возвращает контрольный вариант эксперимента."""
        for v in self.variants:
            if v.is_control:
                return v
        raise ValueError("Experiment must have exactly one control variant")
