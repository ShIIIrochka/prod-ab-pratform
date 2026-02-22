from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.user import User
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_completion import ExperimentOutcome
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.user_role import UserRole


def _make_variant(
    name: str, weight: float, is_control: bool = False
) -> Variant:
    return Variant(
        id=uuid4(), name=name, value=name, weight=weight, is_control=is_control
    )


def _make_experiment(
    status: ExperimentStatus = ExperimentStatus.RUNNING,
) -> Experiment:
    v_control = _make_variant("control", 0.1, is_control=True)
    v_b = _make_variant("B", 0.1)
    return Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Test",
        status=status,
        version=1,
        audience_fraction=0.2,
        variants=[v_control, v_b],
        targeting_rule=None,
        owner_id=str(uuid4()),
    )


def _make_admin() -> User:
    return User(
        id=str(uuid4()),
        email="admin@test.com",
        role=UserRole.ADMIN,
        password="test",
    )


def _make_approver() -> User:
    return User(
        id=str(uuid4()),
        email="approver@test.com",
        role=UserRole.APPROVER,
        password="test",
    )


# ---- complete() — winner_variant_id accepts variant name ----


def test_complete_rollout_winner_by_variant_name():
    """complete() принимает winner_variant_id как имя варианта."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    exp.complete(
        outcome=ExperimentOutcome.ROLLOUT_WINNER,
        comment="B won",
        completed_by=str(uuid4()),
        winner_variant_id="B",
    )
    assert exp.status == ExperimentStatus.COMPLETED
    assert exp.completion is not None
    assert exp.completion.winner_variant_id == "B"


def test_complete_rollout_winner_by_variant_id():
    """complete() принимает winner_variant_id как UUID варианта."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    winner_uuid = str(exp.variants[1].id)
    exp.complete(
        outcome=ExperimentOutcome.ROLLOUT_WINNER,
        comment="B won by UUID",
        completed_by=str(uuid4()),
        winner_variant_id=winner_uuid,
    )
    assert exp.status == ExperimentStatus.COMPLETED


def test_complete_rollout_winner_invalid_variant_raises():
    """complete() с несуществующим вариантом → ValueError (негативный тест)."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    with pytest.raises(ValueError, match="not found"):
        exp.complete(
            outcome=ExperimentOutcome.ROLLOUT_WINNER,
            comment="winner",
            completed_by=str(uuid4()),
            winner_variant_id="NONEXISTENT",
        )


def test_complete_rollback_no_winner_needed():
    """complete() ROLLBACK не требует winner_variant_id."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    exp.complete(
        outcome=ExperimentOutcome.ROLLBACK,
        comment="reverting",
        completed_by=str(uuid4()),
        winner_variant_id=None,
    )
    assert exp.status == ExperimentStatus.COMPLETED
    assert exp.completion.outcome == ExperimentOutcome.ROLLBACK


def test_complete_no_effect():
    """complete() NO_EFFECT не требует winner_variant_id."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    exp.complete(
        outcome=ExperimentOutcome.NO_EFFECT,
        comment="no significant difference",
        completed_by=str(uuid4()),
        winner_variant_id=None,
    )
    assert exp.completion.outcome == ExperimentOutcome.NO_EFFECT


def test_complete_requires_comment():
    """complete() с пустым комментарием → ValueError (негативный тест)."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    with pytest.raises(ValueError):
        exp.complete(
            outcome=ExperimentOutcome.ROLLBACK,
            comment="",
            completed_by=str(uuid4()),
            winner_variant_id=None,
        )


def test_complete_from_invalid_status_raises():
    """complete() из статуса DRAFT → ValueError (негативный тест)."""
    exp = _make_experiment(status=ExperimentStatus.DRAFT)
    with pytest.raises(ValueError):
        exp.complete(
            outcome=ExperimentOutcome.ROLLBACK,
            comment="try",
            completed_by=str(uuid4()),
            winner_variant_id=None,
        )


# ---- Lifecycle transitions ----


def test_send_to_review_from_draft():
    """Переход DRAFT → ON_REVIEW."""
    exp = _make_experiment(status=ExperimentStatus.DRAFT)
    exp.send_to_review()
    assert exp.status == ExperimentStatus.ON_REVIEW


def test_send_to_review_from_non_draft_raises():
    """Переход в ON_REVIEW из не-DRAFT → ValueError (негативный тест)."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    with pytest.raises(ValueError):
        exp.send_to_review()


def test_pause_running():
    """RUNNING → PAUSED."""
    exp = _make_experiment(status=ExperimentStatus.RUNNING)
    exp.pause()
    assert exp.status == ExperimentStatus.PAUSED


def test_pause_non_running_raises():
    """Пауза из не-RUNNING → ValueError (негативный тест)."""
    exp = _make_experiment(status=ExperimentStatus.DRAFT)
    with pytest.raises(ValueError):
        exp.pause()


# ---- Variant validation ----


def test_experiment_must_have_exactly_one_control():
    """Нет контрольного варианта → ValueError (негативный тест)."""
    with pytest.raises(ValueError, match="exactly one control"):
        Experiment(
            id=uuid4(),
            flag_key="f",
            name="E",
            status=ExperimentStatus.DRAFT,
            version=1,
            audience_fraction=0.2,
            variants=[
                _make_variant("A", 0.1, is_control=False),
                _make_variant("B", 0.1, is_control=False),
            ],
            targeting_rule=None,
            owner_id=str(uuid4()),
        )


def test_experiment_weights_must_equal_audience_fraction():
    """Сумма весов != audience_fraction → ValueError (негативный тест)."""
    with pytest.raises(ValueError, match="must equal"):
        Experiment(
            id=uuid4(),
            flag_key="f",
            name="E",
            status=ExperimentStatus.DRAFT,
            version=1,
            audience_fraction=0.3,
            variants=[
                _make_variant("control", 0.1, is_control=True),
                _make_variant("B", 0.1, is_control=False),
            ],
            targeting_rule=None,
            owner_id=str(uuid4()),
        )
