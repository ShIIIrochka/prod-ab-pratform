from __future__ import annotations

from dataclasses import dataclass
from .users import UserAlreadyExistsError, UserNotFoundError
from .decision import (
    FeatureFlagNotFoundError,
    ExperimentNotFoundError,
    VariantNameAlreadyExistsError,
    DuplicateVariantNamesError,
    VariantValueTypeError,
)
from .experiment import CannotReviewExperimentError
from .events import EventTypeAlreadyExistsError, EventTypeNotFoundError
from .auth import CouldNotAuthorizeError
from .feature_flags import FeatureFlagAlreadyExistsError
from .metrics import MetricNotFoundError


@dataclass
class NotEnoughPermissionsException(Exception):
    message = "Not enough permissions"
