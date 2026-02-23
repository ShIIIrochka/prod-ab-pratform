from dataclasses import dataclass


@dataclass
class MetricNotFoundError(Exception):
    message: str = "Metric not found"
