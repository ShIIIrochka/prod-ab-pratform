from dataclasses import dataclass


@dataclass
class CouldNotAuthorizeError(Exception):
    message: str = "Could not authorize user"
