from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metric:
    key: str
    name: str
    calculation_rule: str
    requires_exposure: bool = False
    description: str | None = None
