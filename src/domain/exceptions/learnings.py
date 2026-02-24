from dataclasses import dataclass


@dataclass
class LearningNotFoundError(Exception):
    message: str = "Learning record not found for experiment"
