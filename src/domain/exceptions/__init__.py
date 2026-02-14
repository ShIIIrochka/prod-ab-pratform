from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions.auth import (
    AuthenticationException,
    AuthorizationException,
    InsufficientPermissionsException,
    InvalidCredentialsException,
    InvalidTokenException,
)
from domain.exceptions.base import ApplicationException
from domain.exceptions.decision import FeatureFlagNotFoundException


@dataclass
class NotEnoughPermissionsException(Exception):
    message = "Not enough permissions"

