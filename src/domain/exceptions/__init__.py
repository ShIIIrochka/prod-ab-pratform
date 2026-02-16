from __future__ import annotations

from dataclasses import dataclass
from .users import UserAlreadyExistsError, UserNotFoundError
from .decision import (
    FeatureFlagNotFoundError,
    ExperimentNotFoundError,
    FeatureFlagAlreadyExistsError,
)


@dataclass
class NotEnoughPermissionsException(Exception):
    message = "Not enough permissions"
