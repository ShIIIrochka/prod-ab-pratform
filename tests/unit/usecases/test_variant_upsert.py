"""Unit tests for ExperimentsRepository variant upsert — uses in-memory SQLite, no mocks."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tortoise import Tortoise

from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.infra.adapters.db.models.user import UserModel
from src.infra.adapters.repositories.experiments_repository import (
    ExperimentsRepository,
)


def _make_experiment(
    variants: list[Variant], owner_id: str = "owner-1"
) -> Experiment:
    return Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Test",
        status=ExperimentStatus.DRAFT,
        version=1,
        audience_fraction=0.2,
        variants=variants,
        targeting_rule=None,
        owner_id=owner_id,
    )


@pytest.fixture
async def db():
    """In-memory SQLite for repository tests."""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["src.infra.adapters.db.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
async def owner(db):
    """Create an owner user required by Experiment FK."""
    await UserModel.create(
        id="owner-1",
        email="owner@example.com",
        password="hashed",
        role="experimenter",
    )


@pytest.mark.asyncio
async def test_upsert_existing_variant_does_not_delete(
    db,
    owner,
) -> None:
    """При сохранении с теми же именами вариантов удаление не вызывается."""
    existing_id = uuid4()
    variant = Variant(
        id=existing_id, name="control", value="A", weight=0.1, is_control=True
    )
    variant_b = Variant(
        id=uuid4(), name="B", value="b", weight=0.1, is_control=False
    )
    experiment = _make_experiment([variant, variant_b])

    repo = ExperimentsRepository()
    await repo.save(experiment)

    # Reload and verify both variants exist
    reloaded = await repo.get_by_id(experiment.id)
    assert reloaded is not None
    assert len(reloaded.variants) == 2
    names = {v.name for v in reloaded.variants}
    assert names == {"control", "B"}

    # Save again with same variants — should not break
    await repo.save(experiment)
    reloaded2 = await repo.get_by_id(experiment.id)
    assert reloaded2 is not None
    assert len(reloaded2.variants) == 2


@pytest.mark.asyncio
async def test_upsert_new_variant_creates_it(
    db,
    owner,
) -> None:
    """Новый вариант (не существует в БД) создаётся через save()."""
    variant = Variant(
        id=uuid4(), name="control", value="A", weight=0.1, is_control=True
    )
    variant_new = Variant(
        id=uuid4(), name="C", value="c", weight=0.1, is_control=False
    )
    experiment = _make_experiment([variant, variant_new])

    repo = ExperimentsRepository()
    await repo.save(experiment)

    reloaded = await repo.get_by_id(experiment.id)
    assert reloaded is not None
    assert len(reloaded.variants) == 2
    names = {v.name: v.value for v in reloaded.variants}
    assert names["control"] == "A"
    assert names["C"] == "c"


@pytest.mark.asyncio
async def test_upsert_removes_variant_not_in_incoming(
    db,
    owner,
) -> None:
    """Вариант, отсутствующий во входящем списке, удаляется из БД."""
    variant_a = Variant(
        id=uuid4(), name="A", value="a", weight=0.2, is_control=True
    )
    variant_b = Variant(
        id=uuid4(), name="B", value="b", weight=0.0, is_control=False
    )
    experiment = _make_experiment([variant_a, variant_b])

    repo = ExperimentsRepository()
    await repo.save(experiment)

    reloaded = await repo.get_by_id(experiment.id)
    assert reloaded is not None
    assert len(reloaded.variants) == 2

    # Update: remove B, keep only A (weights must still sum to audience_fraction)
    variant_a_only = Variant(
        id=variant_a.id, name="A", value="a", weight=0.2, is_control=True
    )
    experiment.variants = [variant_a_only]
    await repo.save(experiment)

    reloaded2 = await repo.get_by_id(experiment.id)
    assert reloaded2 is not None
    assert len(reloaded2.variants) == 1
    assert reloaded2.variants[0].name == "A"
