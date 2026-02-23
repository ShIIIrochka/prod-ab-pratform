from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureFlagNotFoundError(Exception):
    message = "Feature flag not found"


@dataclass
class ExperimentNotFoundError(Exception):
    message = "Experiment not found"


@dataclass
class VariantNameAlreadyExistsError(Exception):
    message = "Variant with this name already exists"


@dataclass
class DuplicateVariantNamesError(Exception):
    message = "You have duplicated variant names"


@dataclass
class VariantValueTypeError(Exception):
    message: str = "Variant value does not match feature flag value type"
