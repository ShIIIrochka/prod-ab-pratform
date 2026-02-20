from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AggregationUnit(StrEnum):
    EVENT = "event"
    USER = "user"


@dataclass
class Metric:
    key: str
    name: str
    calculation_rule: str
    description: str | None = None
    aggregation_unit: AggregationUnit = AggregationUnit.EVENT
