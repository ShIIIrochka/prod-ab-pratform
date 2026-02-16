from dataclasses import dataclass


@dataclass
class CannotReviewExperimentError(Exception):
    message: str = "Cannot review experiment"
