from __future__ import annotations

from dataclasses import dataclass
from .users import UserAlreadyExistsError, UserNotFoundError
from .decision import (
    FeatureFlagNotFoundError,
    ExperimentNotFoundError,
    FeatureFlagAlreadyExistsError,
    VariantNameAlreadyExistsError,
    DuplicateVariantNamesError,
    VariantValueTypeError,
)
from .events import EventTypeAlreadyExistsError


@dataclass
class NotEnoughPermissionsException(Exception):
    message = "Not enough permissions"
