from __future__ import annotations

from dataclasses import field, dataclass
from uuid import UUID, uuid4

from domain.aggregates.event import AttributionStatus, Event
from domain.aggregates.event_type import EventType
from domain.aggregates.experiment import Experiment
from domain.aggregates.feature_flag import FeatureFlag
from domain.aggregates.metric import Metric

@dataclass
class BaseEntity:
    id: UUID = field(default_factory=uuid4, kw_only=True)
