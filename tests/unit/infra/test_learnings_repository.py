"""Unit tests for LearningsRepository (OpenSearch adapter)."""

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
from src.infra.adapters.repositories.learnings_repository import (
    LearningsRepository,
    _learning_to_doc,
)


def _make_variant(
    name: str, weight: float, is_control: bool = False
) -> Variant:
    return Variant(
        id=uuid4(), name=name, value=name, weight=weight, is_control=is_control
    )


def _make_completed_experiment() -> Experiment:
    return Experiment(
        id=uuid4(),
        flag_key="button_color",
        name="Test button color",
        status=ExperimentStatus.COMPLETED,
        version=1,
        audience_fraction=0.2,
        variants=[
            _make_variant("control", 0.1, is_control=True),
            _make_variant("B", 0.1),
        ],
        targeting_rule=None,
        owner_id=str(uuid4()),
        target_metric_key="ctr",
        completion=ExperimentCompletion(
            outcome=ExperimentOutcome.ROLLOUT_WINNER,
            winner_variant_id="B",
            comment="B won, rolling out",
            completed_at=datetime.now(UTC),
            completed_by=str(uuid4()),
        ),
    )


@pytest.mark.asyncio
async def test_save_indexes_learning() -> None:
    """save(learning) calls OpenSearch index with document."""
    indexed: list[tuple[str, dict]] = []

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def index(
            self, index: str, id: str, body: dict, refresh: bool = True
        ) -> None:
            indexed.append((id, body))

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    exp = _make_completed_experiment()
    learning = Learning.from_completed_experiment(exp)

    await repo.save(learning)

    assert len(indexed) == 1
    doc_id, doc = indexed[0]
    assert doc_id == str(learning.id)
    assert doc["id"] == str(learning.id)
    assert doc["name"] == "Test button color"
    assert doc["flag_key"] == "button_color"
    assert doc["completion"]["outcome"] == "rollout_winner"
    assert doc["target_metric_key"] == "ctr"
    assert doc["completion"]["comment"] == "B won, rolling out"
    assert doc["hypothesis"] == ""
    assert "context_and_segment" in doc
    assert "links" in doc
    assert "notes" in doc
    assert "tags" in doc


@pytest.mark.asyncio
async def test_save_no_op_when_client_is_none() -> None:
    """save(learning) does nothing when OpenSearch client is not connected."""

    class FakeOpenSearch:
        _client = None

        @property
        def client(self):
            return None

        @property
        def index_name(self) -> str:
            return "learnings"

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    learning = Learning.from_completed_experiment(_make_completed_experiment())
    await repo.save(learning)


@pytest.mark.asyncio
async def test_get_similar_maps_docs_to_learning() -> None:
    """get_similar() returns list[Learning] from _source."""
    search_body: list[dict] = []
    exp1 = _make_completed_experiment()
    exp2 = _make_completed_experiment()
    learning1 = Learning.from_completed_experiment(exp1)
    learning2 = Learning.from_completed_experiment(exp2)
    doc1 = _learning_to_doc(learning1)
    doc2 = _learning_to_doc(learning2)

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def search(self, index: str, body: dict) -> dict:
            search_body.append(body)
            return {
                "hits": {
                    "hits": [
                        {"_id": str(learning1.id), "_source": doc1},
                        {"_id": str(learning2.id), "_source": doc2},
                    ],
                }
            }

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    result = await repo.get_similar(
        limit=10,
        query="button",
        flag_key="button_color",
    )

    assert len(search_body) == 1
    assert search_body[0]["size"] == 10
    assert "query" in search_body[0]
    assert len(result) == 2
    assert result[0].id == learning1.id
    assert result[0].name == learning1.name
    assert result[0].hypothesis == ""
    assert result[1].id == learning2.id
    assert result[1].name == learning2.name


@pytest.mark.asyncio
async def test_get_similar_returns_empty_when_client_is_none() -> None:
    """get_similar() returns [] when OpenSearch client is not connected."""

    class FakeOpenSearch:
        @property
        def client(self):
            return None

        @property
        def index_name(self) -> str:
            return "learnings"

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    result = await repo.get_similar(limit=5)
    assert result == []


@pytest.mark.asyncio
async def test_update_learning_sends_partial_doc() -> None:
    """update_learning(learning) calls OpenSearch update with editable fields."""
    exp = _make_completed_experiment()
    learning = Learning.from_completed_experiment(exp).with_updated_editable(
        hypothesis="H",
        context_and_segment="C",
        links=["https://x.com"],
        notes="N",
        tags=["t1"],
    )
    updated: list[tuple[str, dict]] = []

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def update(
            self,
            index: str,
            id: str,
            body: dict,
            refresh: bool = True,
        ) -> dict:
            updated.append((id, body))
            return {"result": "updated"}

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    await repo.update_learning(learning)

    assert len(updated) == 1
    doc_id, body = updated[0]
    assert doc_id == str(learning.experiment_id)
    assert body["doc"]["hypothesis"] == "H"
    assert body["doc"]["context_and_segment"] == "C"
    assert body["doc"]["links"] == ["https://x.com"]
    assert body["doc"]["notes"] == "N"
    assert body["doc"]["tags"] == ["t1"]


@pytest.mark.asyncio
async def test_get_by_experiment_id_returns_learning() -> None:
    """get_by_experiment_id() returns Learning when doc exists."""
    exp = _make_completed_experiment()
    learning = Learning.from_completed_experiment(exp)
    doc = _learning_to_doc(learning)

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def get(self, index: str, id: str) -> dict:
            return {"_source": doc}

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    record = await repo.get_by_experiment_id(exp.id)

    assert record is not None
    assert record.experiment_id == exp.id
    assert record.name == exp.name
    assert record.hypothesis == ""


@pytest.mark.asyncio
async def test_get_by_experiment_id_returns_none_when_missing() -> None:
    """get_by_experiment_id() returns None when document does not exist."""

    class Err404(Exception):
        status_code = 404

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def get(self, index: str, id: str) -> dict:
            raise Err404("not found")

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    record = await repo.get_by_experiment_id(uuid4())
    assert record is None
