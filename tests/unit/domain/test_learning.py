"""Unit tests for Learning aggregate."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.learning import Learning
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_completion import (
    ExperimentCompletion,
    ExperimentOutcome,
)
from src.domain.value_objects.experiment_status import ExperimentStatus


def _make_variant(
    name: str, weight: float, is_control: bool = False
) -> Variant:
    return Variant(
        id=uuid4(), name=name, value=name, weight=weight, is_control=is_control
    )


def _make_completed_experiment() -> Experiment:
    return Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Exp",
        status=ExperimentStatus.COMPLETED,
        version=1,
        audience_fraction=0.2,
        variants=[
            _make_variant("control", 0.1, is_control=True),
            _make_variant("B", 0.1),
        ],
        targeting_rule=None,
        owner_id="u1",
        completion=ExperimentCompletion(
            outcome=ExperimentOutcome.NO_EFFECT,
            winner_variant_id=None,
            comment="Done",
            completed_at=datetime.now(UTC),
            completed_by="u1",
        ),
    )


def test_from_completed_experiment() -> None:
    exp = _make_completed_experiment()
    learning = Learning.from_completed_experiment(exp)
    assert learning.experiment_id == exp.id
    assert learning.flag_key == exp.flag_key
    assert learning.name == exp.name
    assert learning.outcome == exp.completion.outcome
    assert learning.outcome_comment == exp.completion.comment
    assert learning.hypothesis == ""
    assert learning.context_and_segment == ""
    assert learning.links is None
    assert learning.notes is None
    assert learning.tags is None


def test_from_completed_experiment_raises_without_completion() -> None:
    exp = _make_completed_experiment()
    exp.completion = None
    with pytest.raises(ValueError, match="completion"):
        Learning.from_completed_experiment(exp)


def test_with_updated_editable() -> None:
    exp = _make_completed_experiment()
    learning = Learning.from_completed_experiment(exp)
    updated = learning.with_updated_editable(
        hypothesis="H",
        context_and_segment="C",
        links=["https://x.com"],
        notes="N",
        tags=["t1"],
    )
    assert updated.experiment_id == learning.experiment_id
    assert updated.hypothesis == "H"
    assert updated.context_and_segment == "C"
    assert updated.links == ["https://x.com"]
    assert updated.notes == "N"
    assert updated.tags == ["t1"]
    assert updated.flag_key == learning.flag_key
    assert updated.name == learning.name


def test_with_updated_editable_partial() -> None:
    exp = _make_completed_experiment()
    learning = Learning.from_completed_experiment(exp)
    updated = learning.with_updated_editable(hypothesis="Only hypothesis")
    assert updated.hypothesis == "Only hypothesis"
    assert updated.context_and_segment == learning.context_and_segment
    assert updated.links == learning.links
