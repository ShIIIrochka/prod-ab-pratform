import logging

from datetime import datetime
from uuid import UUID

from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_completion import (
    ExperimentCompletion,
    ExperimentOutcome,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.targeting_rule import TargetingRule
from src.infra.adapters.opensearch.opensearch import OpenSearch


logger = logging.getLogger(__name__)


def _experiment_to_doc(experiment: Experiment) -> dict:
    completion = experiment.completion
    if not completion:
        return {}
    return {
        "id": str(experiment.id),
        "flag_key": experiment.flag_key,
        "name": experiment.name,
        "status": experiment.status.value,
        "version": experiment.version,
        "audience_fraction": experiment.audience_fraction,
        "variants": [
            {
                "id": str(v.id),
                "name": v.name,
                "value": v.value,
                "weight": v.weight,
                "is_control": v.is_control,
            }
            for v in experiment.variants
        ],
        "targeting_rule": (
            experiment.targeting_rule.rule_expression
            if experiment.targeting_rule
            else None
        ),
        "owner_id": experiment.owner_id,
        "target_metric_key": experiment.target_metric_key,
        "metric_keys": experiment.metric_keys or [],
        "guardrails": [
            {
                "id": str(g.id),
                "metric_key": g.metric_key,
                "threshold": g.threshold,
                "observation_window_minutes": g.observation_window_minutes,
                "action": g.action.value,
            }
            for g in experiment.guardrails
        ],
        "completion": {
            "outcome": completion.outcome.value,
            "winner_variant_id": completion.winner_variant_id,
            "comment": completion.comment,
            "completed_at": completion.completed_at.isoformat(),
            "completed_by": completion.completed_by,
        },
        "created_at": experiment.created_at.isoformat(),
        "updated_at": experiment.updated_at.isoformat(),
    }


def _doc_to_experiment(source: dict) -> Experiment | None:
    try:
        exp_id = UUID(source["id"])
    except (KeyError, ValueError, TypeError):
        return None
    status_str = source.get("status", "completed")
    try:
        status = ExperimentStatus(status_str)
    except ValueError:
        status = ExperimentStatus.COMPLETED
    variants_data = source.get("variants") or []
    variants = []
    for v in variants_data:
        try:
            variants.append(
                Variant(
                    id=UUID(v["id"]),
                    name=v["name"],
                    value=v["value"],
                    weight=float(v["weight"]),
                    is_control=bool(v.get("is_control", False)),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    if not variants:
        return None
    targeting_rule = None
    if source.get("targeting_rule"):
        try:
            targeting_rule = TargetingRule(
                rule_expression=source["targeting_rule"]
            )
        except ValueError:
            pass
    guardrails = []
    for g in source.get("guardrails") or []:
        try:
            guardrails.append(
                GuardrailConfig(
                    id=UUID(g["id"]),
                    metric_key=g["metric_key"],
                    threshold=float(g["threshold"]),
                    observation_window_minutes=int(
                        g["observation_window_minutes"]
                    ),
                    action=GuardrailAction(g["action"]),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    completion_data = source.get("completion") or {}
    completed_at_str = completion_data.get("completed_at")
    try:
        completed_at = (
            datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
            if completed_at_str
            else datetime.now()
        )
    except (ValueError, AttributeError):
        completed_at = datetime.now()
    completion = ExperimentCompletion(
        outcome=ExperimentOutcome(completion_data.get("outcome", "no_effect")),
        winner_variant_id=completion_data.get("winner_variant_id"),
        comment=completion_data.get("comment", ""),
        completed_at=completed_at,
        completed_by=completion_data.get("completed_by", ""),
    )
    created_at_str = source.get("created_at")
    updated_at_str = source.get("updated_at")
    try:
        created_at = (
            datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime.now()
        )
    except (ValueError, AttributeError):
        created_at = datetime.now()
    try:
        updated_at = (
            datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            if updated_at_str
            else created_at
        )
    except (ValueError, AttributeError):
        updated_at = created_at
    return Experiment(
        id=exp_id,
        flag_key=source.get("flag_key", ""),
        name=source.get("name", ""),
        status=status,
        version=int(source.get("version", 1)),
        audience_fraction=float(source.get("audience_fraction", 0)),
        variants=variants,
        targeting_rule=targeting_rule,
        owner_id=source.get("owner_id", ""),
        target_metric_key=source.get("target_metric_key") or None,
        metric_keys=source.get("metric_keys") or [],
        guardrails=guardrails,
        completion=completion,
        created_at=created_at,
        updated_at=updated_at,
    )


class LearningsRepository(LearningsRepositoryPort):
    def __init__(self, opensearch: OpenSearch) -> None:
        self._client = opensearch.client
        self._index_name = opensearch.index_name

    async def save(self, experiment: Experiment) -> None:
        if (
            experiment.status != ExperimentStatus.COMPLETED
            or not experiment.completion
        ):
            return
        doc = _experiment_to_doc(experiment)
        if not doc:
            return
        try:
            await self._client.index(
                index=self._index_name,
                id=str(experiment.id),
                body=doc,
                refresh=True,
            )
        except Exception as e:
            logger.exception(
                "Failed to index experiment %s in learnings: %s",
                experiment.id,
                e,
            )
            raise

    async def get_similar(
        self,
        limit: int,
        query: str | None = None,
        flag_key: str | None = None,
        owner_id: str | None = None,
        outcome: ExperimentOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        target_metric_key: str | None = None,
    ) -> list[Experiment]:
        try:
            must = []
            filter_clauses = []

            if flag_key:
                filter_clauses.append({"term": {"flag_key": flag_key}})
            if owner_id:
                filter_clauses.append({"term": {"owner_id": owner_id}})
            if outcome:
                filter_clauses.append({"term": {"outcome": outcome.value}})
            if target_metric_key:
                filter_clauses.append(
                    {"term": {"target_metric_key": target_metric_key}}
                )
            if date_from or date_to:
                range_q: dict = {"completed_at": {}}
                if date_from:
                    range_q["completed_at"]["gte"] = date_from.isoformat()
                if date_to:
                    range_q["completed_at"]["lte"] = date_to.isoformat()
                filter_clauses.append({"range": range_q})

            if query and query.strip():
                must.append(
                    {
                        "multi_match": {
                            "query": query.strip(),
                            "fields": ["search_text", "name", "comment"],
                        }
                    }
                )

            body: dict = {
                "size": limit,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"completed_at": {"order": "desc"}},
                ],
            }
            if must or filter_clauses:
                body["query"] = {"bool": {}}
                if must:
                    body["query"]["bool"]["must"] = must
                if filter_clauses:
                    body["query"]["bool"]["filter"] = filter_clauses
            else:
                body["query"] = {"match_all": {}}

            response = await self._client.search(
                index=self._index_name,
                body=body,
            )
        except Exception as e:
            logger.exception("Learnings search failed: %s", e)
            return []

        hits = response.get("hits", {}).get("hits", [])
        result: list[Experiment] = []
        for hit in hits:
            source = hit.get("_source") or {}
            exp = _doc_to_experiment(source)
            if exp is not None:
                result.append(exp)
        return result
