from dataclasses import dataclass


@dataclass
class UserNotFoundError(Exception):
    message = "User not found"


@dataclass
class UserAlreadyExistsError(Exception):
    message = "User with this email already exists"
