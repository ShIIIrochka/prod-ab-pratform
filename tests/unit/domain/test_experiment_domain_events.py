"""Tests that Experiment aggregate correctly emits domain events on lifecycle transitions."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.user import User
from src.domain.entities.variant import Variant
from src.domain.events.experiment import (
    ExperimentEventType,
    ExperimentStatusChanged,
)
from src.domain.value_objects.approval import Approval
from src.domain.value_objects.experiment_completion import ExperimentOutcome
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.user_role import UserRole


def _make_experiment(
    status: ExperimentStatus = ExperimentStatus.DRAFT,
) -> Experiment:
    return Experiment(
        flag_key="btn_color",
        name="Button Experiment",
        status=status,
        version=1,
        audience_fraction=0.5,
        variants=[
            Variant(
                id=uuid4(),
                name="control",
                value="blue",
                weight=0.25,
                is_control=True,
            ),
            Variant(
                id=uuid4(),
                name="treatment",
                value="red",
                weight=0.25,
                is_control=False,
            ),
        ],
        targeting_rule=None,
        owner_id="owner-1",
    )


def _make_admin() -> User:
    return User(
        id="admin-1",
        email="admin@example.com",
        password="x",
        role=UserRole.ADMIN,
    )


def test_send_to_review_emits_event() -> None:
    exp = _make_experiment()
    exp.send_to_review()

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], ExperimentStatusChanged)
    assert events[0].event_type == ExperimentEventType.SENT_TO_REVIEW
    assert events[0].experiment_id == exp.id


def test_pop_clears_event_queue() -> None:
    exp = _make_experiment()
    exp.send_to_review()
    exp.pop_domain_events()
    assert exp.pop_domain_events() == []


def test_approved_emits_only_when_threshold_reached() -> None:
    exp = _make_experiment(ExperimentStatus.ON_REVIEW)
    admin = _make_admin()
    exp.approve(admin, admin)

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.APPROVED
    assert events[0].extra.get("approver_id") == admin.id


def test_reject_emits_event() -> None:
    exp = _make_experiment(ExperimentStatus.ON_REVIEW)
    admin = _make_admin()
    exp.reject(admin, admin)

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.REJECTED


def test_request_changes_emits_event_with_comment() -> None:
    exp = _make_experiment(ExperimentStatus.ON_REVIEW)
    admin = _make_admin()
    exp.request_changes(admin, admin, comment="please fix")

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.CHANGES_REQUESTED
    assert events[0].extra.get("comment") == "please fix"


def test_launch_emits_event() -> None:
    from datetime import datetime

    exp = _make_experiment(ExperimentStatus.APPROVED)
    # `can_be_launched` requires at least one approval when owner has no group
    exp.approvals.append(
        Approval(user_id="admin-1", comment=None, timestamp=datetime.utcnow())
    )
    admin = _make_admin()
    exp.launch(admin, admin)

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.LAUNCHED


def test_pause_emits_event() -> None:
    exp = _make_experiment(ExperimentStatus.RUNNING)
    exp.pause()

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.PAUSED


def test_complete_emits_event_with_outcome() -> None:
    exp = _make_experiment(ExperimentStatus.RUNNING)
    exp.complete(
        outcome=ExperimentOutcome.ROLLBACK,
        comment="did not improve",
        completed_by="analyst-1",
        winner_variant_id=None,
    )

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.COMPLETED
    assert events[0].extra["outcome"] == ExperimentOutcome.ROLLBACK.value


def test_archive_emits_event() -> None:
    exp = _make_experiment(ExperimentStatus.COMPLETED)
    exp.archive()

    events = exp.pop_domain_events()
    assert len(events) == 1
    assert events[0].event_type == ExperimentEventType.ARCHIVED


def test_failed_transition_does_not_emit_event() -> None:
    exp = _make_experiment(ExperimentStatus.DRAFT)
    with pytest.raises(ValueError):
        exp.pause()
    assert exp.pop_domain_events() == []
