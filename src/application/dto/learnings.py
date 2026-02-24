from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.experiment_completion import ExperimentOutcome


class GetSimilarCriteria(BaseModel):
    query: str | None = Field(None, description="Full-text search query")
    flag_key: str | None = Field(None, description="Filter by feature flag key")
    owner_id: str | None = Field(None, description="Filter by experiment owner")
    outcome: ExperimentOutcome | None = Field(
        None, description="Filter by completion outcome"
    )
    date_from: datetime | None = Field(
        None, description="Filter by completed_at >= date_from"
    )
    date_to: datetime | None = Field(
        None, description="Filter by completed_at <= date_to"
    )
    target_metric_key: str | None = Field(
        None, description="Filter by primary metric key"
    )
    limit: int = Field(20, ge=1, le=100, description="Max results to return")


class UpdateLearningRequest(BaseModel):
    hypothesis: str | None = Field(
        None, description="What we wanted to improve and why"
    )
    context_and_segment: str | None = Field(
        None,
        description="Flag key, product zone, targeting, platform/countries/versions",
    )
    links: list[str] | None = Field(
        None,
        description="Links to report/dashboard, ticket/PRD",
    )
    notes: str | None = Field(
        None,
        description="Short insights on why it turned out that way",
    )
    tags: list[str] | None = Field(
        None,
        description="Product zone tags for search",
    )


class LearningResponse(BaseModel):
    id: UUID = Field(..., description="Learning UUID")
    experiment_id: UUID = Field(..., description="Experiment UUID")
    hypothesis: str | None = Field(default=None, description="Hypothesis")
    context_and_segment: str | None = Field(
        default="", description="Context and segment"
    )
    links: list[str] | None = Field(default_factory=list, description="Links")
    notes: str | None = Field(None, description="Notes")
    tags: list[str] | None = Field(None, description="Tags")
    flag_key: str = Field(..., description="Feature flag key")
    name: str = Field(..., description="Experiment name")
    target_metric_key: str | None = Field(
        None, description="Primary metric key"
    )
    outcome: ExperimentOutcome = Field(..., description="Completion outcome")
    outcome_comment: str = Field(..., description="Completion comment")
    completed_at: datetime = Field(..., description="Completed at")
    completed_by: str = Field(..., description="Completed by")
    owner_id: str = Field(..., description="Owner user ID")

    model_config = ConfigDict(from_attributes=True)


class SimilarExperimentsListResponse(BaseModel):
    learnings: list[LearningResponse] = Field(
        ..., description="List of learnings"
    )
