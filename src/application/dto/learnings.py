from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.value_objects.experiment_completion import ExperimentOutcome


class GetSimilarCriteria(BaseModel):
    """Search criteria for similar experiments (learnings library)."""

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
