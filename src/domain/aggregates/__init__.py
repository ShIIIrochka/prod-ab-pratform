from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class BaseEntity:
    id: UUID = field(default_factory=uuid4, kw_only=True)
