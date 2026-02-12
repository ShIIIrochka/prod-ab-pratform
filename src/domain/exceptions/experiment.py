from dataclasses import dataclass


@dataclass
class CannotReviewExperimentError(Exception):
    msg: str = "Cannot review experiment"
