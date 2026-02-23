from dataclasses import dataclass


@dataclass
class FeatureFlagAlreadyExistsError(Exception):
    message: str = "Feature flag with this key already exists"
