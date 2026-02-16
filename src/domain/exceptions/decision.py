from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureFlagNotFoundError(Exception):
    message = "Feature flag not found"


@dataclass
class ExperimentNotFoundError(Exception):
    message = "Experiment not found"


@dataclass
class FeatureFlagAlreadyExistsError(Exception):
    message = "Feature flag with this key already exists"
