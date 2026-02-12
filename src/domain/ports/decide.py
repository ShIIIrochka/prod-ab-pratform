"""Ports for the decide (decision engine) flow. Read-only dependencies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.aggregates.experiment import Experiment
from domain.aggregates.feature_flag import FeatureFlag


@runtime_checkable
class FeatureFlagResolver(Protocol):
    """Resolves feature flag by key. Returns None if flag does not exist."""

    def get_flag(self, flag_key: str) -> FeatureFlag | None: ...


@runtime_checkable
class ActiveExperimentResolver(Protocol):
    """Resolves the active (RUNNING) experiment for a flag.
    Returns (experiment, rollback_to_control_active).
    Only one active experiment per flag (per invariant 2.3.1).
    """

    def get_active_experiment(
        self, flag_key: str
    ) -> tuple[Experiment | None, bool]:
        """Returns (experiment or None, rollback_to_control_active)."""
        ...


@runtime_checkable
class ParticipationPolicy(Protocol):
    """Determines if a subject can participate in an experiment (B5-6).
    When False, the experiment is not applied and default is returned.
    """

    def can_participate(
        self,
        subject_id: str,
        experiment_id: str,
        applied_experiment_ids: list[str],
    ) -> bool:
        """Returns True if the subject may participate in this experiment.
        applied_experiment_ids: experiment ids already applied in this request (for limit).
        """
        ...


@runtime_checkable
class DecisionIdGenerator(Protocol):
    """Generates a unique decision_id for attribution and idempotency."""

    def generate(
        self,
        subject_id: str,
        flag_key: str,
        experiment_id: str | None,
        variant_id: str | None,
    ) -> str: ...
